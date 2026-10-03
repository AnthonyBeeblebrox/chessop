#!/usr/bin/env bash
# Provision a fresh Debian 13 VPS for chessop (public spec §14, ADR 0007), or bring one back in
# line with this directory: every step checks before it changes, so the script is safe to re-run
# after editing anything here. Run it as root from a checkout of the repository:
#
#     sudo deploy/provision.sh
#
# It installs the system, not chessop: the first deploy (deploy.sh) checks a release out behind
# /opt/chessop/current, and only then do chessop's units and timers start doing anything.
set -euo pipefail

UV_VERSION=0.11.9
UV_SHA256=5c43f82077ff0cd5aec588286cbabd89913e4d045bd4e8aa60b20b3ecffc36e3
PYTHON_VERSION=3.12
GOATCOUNTER_VERSION=v2.7.0
GOATCOUNTER_SHA256=98d221cb9c8ef2bf76d8daa9cca647839f8d8b0bb5bc7400ff9337c5da834511

OPT=/opt/chessop
PYTHON_DIR=$OPT/python  # uv-managed CPython, not Debian's
DATA=/var/lib/chessop
CONFIG=/etc/chessop
LIBEXEC=/usr/local/lib/chessop
SHARE=/usr/share/chessop
GOATCOUNTER_DATA=/var/lib/goatcounter
GOATCOUNTER_DB=$GOATCOUNTER_DATA/goatcounter.sqlite3
UNITS=(
	chessop.service
	chessop-maintain.service chessop-maintain.timer
	chessop-disk.service chessop-disk.timer
	chessop-digest.service chessop-digest.timer
	chessop-notify@.service
	goatcounter.service
)
TIMERS=(chessop-maintain.timer chessop-disk.timer chessop-digest.timer)
SCRIPTS=(disk-check error-digest notify-failure goatcounter-retention)  # what the units run

here=$(dirname "$(readlink -f "$0")")
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

say() { printf 'provision: %s\n' "$*"; }
die() { printf 'provision: %s\n' "$*" >&2; exit 1; }

# Put $1 at $2 with mode $3 and owner $4 (default root:root). Succeeds only when the content
# changed, so a caller can restart what reads it; the mode and owner are set either way.
place() {
	local source=$1 target=$2 mode=$3 owner=${4:-root:root} changed=1
	if ! cmp --silent "$source" "$target"; then
		install --mode="$mode" --owner="${owner%:*}" --group="${owner#*:}" "$source" "$target"
		say "installed $target"
		changed=0
	fi
	chmod "$mode" "$target"
	chown "$owner" "$target"
	return "$changed"
}

# Download $1 to $2 and check it against the SHA-256 $3; stop on a mismatch.
fetch() {
	local url=$1 target=$2 sha256=$3
	curl --fail --silent --show-error --location --output "$target" "$url"
	echo "$sha256  $target" | sha256sum --check --status ||
		die "$url does not match its pinned SHA-256"
}

system_user() {
	local name=$1 home=$2
	if ! id -u "$name" >/dev/null 2>&1; then
		useradd --system --user-group --home-dir "$home" --no-create-home \
			--shell /usr/sbin/nologin "$name"
		say "created user $name"
	fi
}

preflight() {
	[ "$(id -u)" -eq 0 ] || die "run as root (sudo deploy/provision.sh)"
	# shellcheck source=/dev/null
	. /etc/os-release
	[ "${ID:-}" = debian ] && [ "${VERSION_ID:-}" = 13 ] || die "this is for Debian 13"
	[ "$(dpkg --print-architecture)" = amd64 ] || die "the pinned binaries are for amd64"
	# Password login goes off below: refuse to lock the owner out.
	local keys
	for keys in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
		[ -s "$keys" ] && return 0
	done
	die "no SSH authorized_keys on this machine: add the owner's key before password login goes off"
}

packages() {
	export DEBIAN_FRONTEND=noninteractive
	apt-get update --quiet=2
	apt-get install --yes --quiet=2 --no-install-recommends \
		ca-certificates curl git sqlite3 caddy ufw unattended-upgrades
}

users() {
	system_user chessop "$DATA"
	system_user goatcounter "$GOATCOUNTER_DATA"
}

uv_and_python() {
	if [ "$(/usr/local/bin/uv --version 2>/dev/null | cut -d' ' -f2)" != "$UV_VERSION" ]; then
		local name=uv-x86_64-unknown-linux-gnu
		fetch "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$name.tar.gz" \
			"$work/uv.tar.gz" "$UV_SHA256"
		tar --extract --gzip --file="$work/uv.tar.gz" --directory="$work"
		install --mode=0755 "$work/$name/uv" "$work/$name/uvx" /usr/local/bin/
		say "installed uv $UV_VERSION"
	fi
	install --directory --mode=0755 "$OPT" "$OPT/releases" "$PYTHON_DIR"
	# Does nothing once this uv's CPython 3.12 is there.
	UV_PYTHON_INSTALL_DIR=$PYTHON_DIR /usr/local/bin/uv python install --no-bin "$PYTHON_VERSION"
}

layout() {
	# Releases are root-owned and readable by chessop; the data only chessop reads.
	install --directory --mode=0700 --owner=chessop --group=chessop "$DATA"
	install --directory --mode=0750 --owner=root --group=chessop "$CONFIG"
	if [ ! -e "$CONFIG/chessop.env" ]; then
		install --mode=0640 --owner=root --group=chessop "$here/chessop.env.example" \
			"$CONFIG/chessop.env"
		say "installed $CONFIG/chessop.env from the example: fill in its blanks"
	fi
	chmod 0640 "$CONFIG/chessop.env"
	chown root:chessop "$CONFIG/chessop.env"
	install --directory --mode=0755 "$LIBEXEC" "$SHARE"
	local script
	for script in "${SCRIPTS[@]}"; do
		place "$here/$script" "$LIBEXEC/$script" 0755 || true
	done
	place "$here/back-in-a-moment.html" "$SHARE/back-in-a-moment.html" 0644 || true
}

journal() {
	install --directory --mode=0755 /etc/systemd/journald.conf.d
	if place "$here/journald.conf" /etc/systemd/journald.conf.d/chessop.conf 0644; then
		systemctl restart systemd-journald.service
	fi
}

ssh_keys_only() {
	# sshd keeps the first value it reads and its drop-ins load in name order: 00- comes before
	# a cloud image's 50-cloud-init.conf, which may turn password login back on.
	local target=/etc/ssh/sshd_config.d/00-chessop.conf
	if place "$here/sshd.conf" "$target" 0644; then
		if ! sshd -t; then
			rm -f "$target"  # so the next run tries again
			die "sshd rejects $target; removed it"
		fi
		systemctl reload ssh.service
	fi
	# The whole output first: under pipefail, `grep --quiet` closing the pipe early would make
	# sshd exit on SIGPIPE and fail the check it had passed.
	local effective
	effective=$(sshd -T)
	grep --quiet --fixed-strings --line-regexp 'passwordauthentication no' <<<"$effective" ||
		die "sshd still allows password login: another file in /etc/ssh sets it first"
}

upgrades() {
	place "$here/20auto-upgrades" /etc/apt/apt.conf.d/20auto-upgrades 0644 || true
}

firewall() {
	ufw default deny incoming >/dev/null
	ufw default allow outgoing >/dev/null
	ufw allow 22/tcp >/dev/null
	ufw allow 80/tcp >/dev/null
	ufw allow 443 >/dev/null  # tcp, and udp for HTTP/3
	ufw --force enable >/dev/null
}

install_goatcounter() {
	local installed
	installed=$(/usr/local/bin/goatcounter version 2>/dev/null || true)
	if ! grep --quiet "version=$GOATCOUNTER_VERSION;" <<<"$installed"; then
		local name="goatcounter-$GOATCOUNTER_VERSION-linux-amd64"
		fetch "https://github.com/arp242/goatcounter/releases/download/$GOATCOUNTER_VERSION/$name.gz" \
			"$work/goatcounter.gz" "$GOATCOUNTER_SHA256"
		gunzip "$work/goatcounter.gz"
		install --mode=0755 "$work/goatcounter" /usr/local/bin/goatcounter
		say "installed GoatCounter $GOATCOUNTER_VERSION"
		restart_goatcounter=yes
	fi
	install --directory --mode=0700 --owner=goatcounter --group=goatcounter "$GOATCOUNTER_DATA"
}

units() {
	local unit changed=()
	for unit in "${UNITS[@]}"; do
		if place "$here/$unit" "/etc/systemd/system/$unit" 0644; then
			changed+=("$unit")
		fi
	done
	systemctl daemon-reload
	# chessop and GoatCounter each wait for what makes them useful (a deployed release, a created
	# site), so enabling them now is safe; their timers likewise.
	systemctl enable --quiet chessop.service goatcounter.service "${TIMERS[@]}"
	for unit in "${changed[@]}"; do
		case $unit in
			*.timer | chessop.service) systemctl try-restart "$unit" ;;
			goatcounter.service) restart_goatcounter=yes ;;
		esac
	done
	if [ -n "${restart_goatcounter:-}" ]; then
		systemctl try-restart goatcounter.service
	fi
	systemctl start chessop.service goatcounter.service "${TIMERS[@]}"
}

configure_caddy() {
	caddy validate --config "$here/Caddyfile" --adapter caddyfile >/dev/null 2>&1 ||
		die "deploy/Caddyfile does not validate: caddy validate --config deploy/Caddyfile"
	systemctl enable --now --quiet caddy.service
	if place "$here/Caddyfile" /etc/caddy/Caddyfile 0644; then
		systemctl reload caddy.service
	fi
}

next_steps() {
	if [ ! -e "$GOATCOUNTER_DB" ]; then
		say "GoatCounter waits for its site. Create it and its login, then start it:"
		say "  sudo -u goatcounter /usr/local/bin/goatcounter db create site -createdb \\"
		say "    -db sqlite+$GOATCOUNTER_DB -vhost stats.chessop.fr -user.email <owner email>"
		say "  sudo systemctl start goatcounter"
	fi
	if [ ! -e "$OPT/current" ]; then
		say "no release yet: chessop starts with the first deploy (deploy.sh)"
	fi
}

restart_goatcounter=
preflight
packages
users
uv_and_python
layout
journal
ssh_keys_only
upgrades
firewall
install_goatcounter
units
configure_caddy
next_steps
say "done"
