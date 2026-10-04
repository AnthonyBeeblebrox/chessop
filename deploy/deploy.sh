#!/usr/bin/env bash
# Deploy a published release to the VPS (public spec §14, ADR 0007). Run it by hand on the
# owner's machine, with the owner's SSH key; it asks for the admin user's sudo password there:
#
#     deploy/deploy.sh vX.Y.Z
#
# Here, it finds the commit the public repository tags vX.Y.Z and refuses unless CI's run for
# that tag finished green. Then on the VPS, as root: it checks that commit out into
# /opt/chessop/releases/vX.Y.Z, installs its locked dependencies, copies the database into the
# pre-deploy folder (the last 3 kept), points /opt/chessop/current at the release and restarts
# chessop. If /healthz does not answer within 30 s it points current back at the release before
# and restarts again. It never restores the database: going back past a migration means
# restoring the pre-deploy copy by hand (docs/operating.md). The last 3 releases are kept.
#
# CHESSOP_SSH (default chessop.fr) is the ssh destination; CHESSOP_GITHUB (default
# AnthonyBeeblebrox/chessop) the public repository. Here it needs git, curl and jq.
set -euo pipefail
shopt -s inherit_errexit  # a failure inside $(...) stops the script too

GITHUB=${CHESSOP_GITHUB:-AnthonyBeeblebrox/chessop}
SSH_DESTINATION=${CHESSOP_SSH:-chessop.fr}
WORKFLOW=ci.yml  # .github/workflows/ci.yml

# On the VPS, as provision.sh lays it out.
OPT=/opt/chessop
RELEASES=$OPT/releases
CURRENT=$OPT/current
PYTHON_DIR=$OPT/python
UV=/usr/local/bin/uv
DATA=/var/lib/chessop
DATABASE=$DATA/chessop.sqlite
PRE_DEPLOY=$DATA/pre-deploy
HEALTHZ=http://127.0.0.1:8000/healthz
HEALTH_SECONDS=30
KEEP=3  # releases, and pre-deploy copies

say() { printf 'deploy: %s\n' "$*"; }
die() { printf 'deploy: %s\n' "$*" >&2; exit 1; }

# --- On the owner's machine ---------------------------------------------------------------------

# The commit the public repository's tag $2 points at.
tagged_commit() {
	local url=$1 version=$2 refs sha
	# An annotated tag lists twice: the tag object, then the commit as `<tag>^{}`, which a
	# pattern must name to match.
	refs=$(git ls-remote --tags "$url" "refs/tags/$version" "refs/tags/$version^{}")
	sha=$(awk -v ref="refs/tags/$version^{}" '$2 == ref { print $1 }' <<<"$refs")
	[ -n "$sha" ] || sha=$(awk -v ref="refs/tags/$version" '$2 == ref { print $1 }' <<<"$refs")
	[ -n "$sha" ] || die "github.com/$GITHUB has no tag $version: publish it first (deploy/publish.sh $version)"
	printf '%s\n' "$sha"
}

# Refuse unless the latest CI run for a push of commit $1 (tag $2) finished green. Any push of
# that commit counts: when a branch and its tag go up in one push, GitHub may run CI for the
# branch alone, and the checks are the commit's either way.
ci_green() {
	local sha=$1 version=$2 runs verdict
	runs=$(curl --fail --silent --show-error --location \
		--header 'Accept: application/vnd.github+json' \
		"https://api.github.com/repos/$GITHUB/actions/workflows/$WORKFLOW/runs?head_sha=$sha&event=push&per_page=100")
	verdict=$(jq --raw-output '
		[.workflow_runs[]] | sort_by(.created_at) | last
		| if . == null then "none" else "\(.status) \(.conclusion)" end' <<<"$runs")
	case $verdict in
		"completed success") say "CI is green for $version" ;;
		none) die "CI has no run for the tag $version yet" ;;
		completed\ *) die "CI failed for $version (${verdict#completed }): not deploying it" ;;
		*) die "CI for $version is still ${verdict% *}: wait for it to finish" ;;
	esac
}

# Check, then run this same script on the VPS as root. It travels base64-encoded inside the ssh
# command, so that stdin and the terminal stay free for sudo's password prompt.
from_here() {
	local version=$1 url sha payload
	[[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "usage: deploy/deploy.sh vX.Y.Z"
	url="https://github.com/$GITHUB.git"
	sha=$(tagged_commit "$url" "$version")
	ci_green "$sha" "$version"
	payload=$(base64 <"${BASH_SOURCE[0]}" | tr -d '\n')
	say "deploying $version (${sha:0:12}) to $SSH_DESTINATION"
	# Every word below is base64, a checked version, a GitHub URL or a hex id: nothing to quote.
	# shellcheck disable=SC2029  # $payload and the arguments are meant to expand here
	ssh -t "$SSH_DESTINATION" \
		"sudo bash -c \"\$(echo $payload | base64 -d)\" deploy.sh --on-vps $version $url $sha"
}

# --- On the VPS, as root -------------------------------------------------------------------------

# Clone the tag into $1 and check it is the commit CI ran on.
check_out() {
	local release=$1 version=$2 url=$3 sha=$4
	rm -rf "$release"  # left by an earlier attempt; never the live release (checked before)
	git clone --quiet --depth 1 --branch "$version" --config advice.detachedHead=false \
		"$url" "$release"
	[ "$(git -C "$release" rev-parse HEAD)" = "$sha" ] ||
		die "the tag $version moved since CI ran: not deploying it"
}

dependencies() {
	local release=$1
	# The pinned CPython provision.sh installed, never a download; bytecode compiled now, since
	# the release is read-only to chessop.
	(cd "$release" && UV_PYTHON_INSTALL_DIR=$PYTHON_DIR UV_PYTHON_DOWNLOADS=never \
		"$UV" sync --frozen --no-dev --compile-bytecode --quiet)
}

# Delete all but the $KEEP most recently changed entries of the folder $1 named $2, never $3.
keep_newest() {
	local folder=$1 name=$2 spare=${3:-} old
	find "$folder" -mindepth 1 -maxdepth 1 -name "$name" -printf '%T@ %p\n' | sort -rn |
		tail -n +$((KEEP + 1)) | cut -d' ' -f2- |
		while IFS= read -r old; do
			if [ "$old" != "$spare" ]; then
				rm -rf "$old"
				say "removed $old"
			fi
		done
}

# Copy the database through SQLite's backup API, as chessop, before the new release can
# migrate it, into $before. Each attempt gets its own copy: a retry after a rollback must not
# overwrite the copy taken before the first attempt migrated anything. A first deploy has no
# database yet.
pre_deploy_copy() {
	local version=$1
	if [ ! -e "$DATABASE" ]; then
		say "no database yet: no pre-deploy copy"
		return
	fi
	install --directory --mode=0700 --owner=chessop --group=chessop "$PRE_DEPLOY"
	before=$PRE_DEPLOY/chessop-$version-$(date --utc +%Y%m%dT%H%M%SZ).sqlite
	runuser -u chessop -- sqlite3 "$DATABASE" ".backup '$before'"
	say "copied the database to $before"
	keep_newest "$PRE_DEPLOY" 'chessop-v*.sqlite'
}

point_current_at() {
	ln -sfn "$1" "$CURRENT.new"
	mv --no-target-directory --force "$CURRENT.new" "$CURRENT"  # in one rename
	touch --no-dereference "$1"  # the most recently deployed, for keep_newest
}

restart() {
	systemctl reset-failed chessop.service 2>/dev/null || true  # a past start limit
	systemctl restart chessop.service || say "chessop.service did not restart cleanly"
}

healthy() {
	local deadline=$((SECONDS + HEALTH_SECONDS))
	while [ "$SECONDS" -lt "$deadline" ]; do
		if curl --fail --silent --max-time 2 --output /dev/null "$HEALTHZ"; then
			return 0
		fi
		sleep 1
	done
	return 1
}

on_vps() {
	local version=$1 url=$2 sha=$3 release previous
	[ "$(id -u)" -eq 0 ] || die "on the VPS this runs as root"
	[ -d "$RELEASES" ] && [ -x "$UV" ] || die "the VPS is not provisioned: run deploy/provision.sh first"
	umask 022  # the release is root's, readable by chessop
	release=$RELEASES/$version
	previous=$(readlink "$CURRENT" || true)
	[ "$previous" != "$release" ] || die "$version is already live"

	# A release that never went live, or was switched back from, is not left behind: the
	# releases kept are ones that went live.
	discard=$release
	trap 'rm -rf "$discard"' EXIT
	check_out "$release" "$version" "$url" "$sha"
	dependencies "$release"
	before=
	pre_deploy_copy "$version"
	discard=  # from here on current may point at it
	point_current_at "$release"
	restart
	if healthy; then
		say "$version is live"
		keep_newest "$RELEASES" 'v*' "$release"
		return
	fi

	journalctl --unit=chessop.service --lines=20 --no-pager >&2 || true
	if [ -z "$previous" ]; then
		die "$version does not answer $HEALTHZ within ${HEALTH_SECONDS} s, and no release came before it"
	fi
	point_current_at "$previous"
	discard=$release
	restart
	local state="does not answer either: look at journalctl -u chessop"
	if healthy; then
		state="answers"
	fi
	die "$version does not answer $HEALTHZ within ${HEALTH_SECONDS} s: current points back at ${previous##*/}, which $state. The database is as $version left it; if $version migrated it, restore the copy taken before it by hand (docs/operating.md, Restore from a backup): ${before:-none was taken}"
}

if [ "${1:-}" = --on-vps ]; then
	shift
	on_vps "$@"
else
	from_here "${1:-}"
fi
