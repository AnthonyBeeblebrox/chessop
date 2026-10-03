#!/usr/bin/env bash
# Publish a release from this private repository to the public one (public spec §14, ADR 0007).
# Run it by hand from a clean main:
#
#     deploy/publish.sh vX.Y.Z
#
# It runs ruff and pytest, tags the private commit vX.Y.Z, takes its tree minus the paths in
# deploy/public-exclude, refuses if that tree holds a secret, commits it as one squashed
# "Release vX.Y.Z" on the local `public` branch, and pushes that commit to the public
# repository's main with the tag vX.Y.Z. Locally the public commit's tag is public/vX.Y.Z,
# since vX.Y.Z names the private commit. CI on GitHub then runs the checks again; nothing ships
# until deploy.sh is run by hand.
#
# CHESSOP_PUBLIC_REMOTE (default github) names the git remote of the public repository:
#
#     git remote add github git@github.com:AnthonyBeeblebrox/chessop.git
set -euo pipefail
shopt -s inherit_errexit  # a failure inside $(...) stops the script too

REMOTE=${CHESSOP_PUBLIC_REMOTE:-github}
BRANCH=public       # here: one commit per release, no private history
REMOTE_BRANCH=main  # there
EXCLUDE=deploy/public-exclude
# What must never be published, as extended regular expressions matched without regard to case:
# a Lichess token (personal lip_, OAuth lio_); a Scaleway access key (SCW...); a Scaleway
# secret key, which is a bare UUID and so is matched only where a secret, key or token is
# given one; an age secret key.
UUID='[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
SECRETS=(
	'\bli[op]_[A-Za-z0-9]{12,}'
	'\bSCW[A-Z0-9]{17}\b'
	"(secret|key|token)[a-z_]*[\"']?[[:space:]]*[:=][[:space:]]*[\"']?$UUID"
	'AGE-SECRET-KEY-1[0-9A-Z]{50,}'
)

say() { printf 'publish: %s\n' "$*"; }
die() { printf 'publish: %s\n' "$*" >&2; exit 1; }

preflight() {
	[[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "usage: deploy/publish.sh vX.Y.Z"
	[ "$(git symbolic-ref --quiet --short HEAD)" = main ] || die "publish from main"
	[ -z "$(git status --porcelain)" ] || die "main is dirty: commit or stash first"
	local tag
	for tag in "$version" "public/$version"; do
		! git rev-parse --quiet --verify "refs/tags/$tag" >/dev/null ||
			die "the tag $tag already exists: $version is published"
	done
	git remote get-url "$REMOTE" >/dev/null 2>&1 ||
		die "no remote $REMOTE: git remote add $REMOTE git@github.com:AnthonyBeeblebrox/chessop.git"
}

checks() {
	say "running ruff and pytest"
	uv run --locked ruff check . || die "ruff check fails"
	uv run --locked ruff format --check . || die "ruff format --check fails"
	uv run --locked pytest --quiet || die "pytest fails"
}

# The tree of HEAD minus the excluded paths, written to the object store: its id.
public_tree() {
	local index pathspecs=() line
	index=$(mktemp)
	rm -f "$index"  # git wants to create the index itself
	while IFS= read -r line; do
		line=${line%%#*}
		line=${line%"${line##*[![:space:]]}"}
		[ -z "$line" ] || pathspecs+=(":(glob)$line")
	done <"$EXCLUDE"
	GIT_INDEX_FILE=$index git read-tree HEAD
	GIT_INDEX_FILE=$index git rm --cached -r --quiet --ignore-unmatch -- "${pathspecs[@]}"
	GIT_INDEX_FILE=$index git write-tree
	rm -f "$index"
}

# Refuse when the tree holds a secret, naming where (path:line), never what.
scan() {
	local tree=$1 patterns=() pattern hits status=0
	for pattern in "${SECRETS[@]}"; do
		patterns+=(-e "$pattern")
	done
	hits=$(git grep -I -i -n -E "${patterns[@]}" "$tree" --) || status=$?
	case $status in
		0)
			cut -d: -f2,3 <<<"$hits" | sed 's/^/  /' >&2
			die "a secret pattern is in the public tree (above): remove it, or exclude its path"
			;;
		1) ;;  # nothing found
		*) die "the secret scan failed" ;;
	esac
}

release() {
	local tree=$1 parent commit
	git tag --annotate --message="Release $version" "$version" HEAD
	parent=$(git rev-parse --quiet --verify "refs/heads/$BRANCH" || true)
	commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "Release $version")
	git update-ref -m "publish $version" "refs/heads/$BRANCH" "$commit" "$parent"
	git tag --annotate --message="Release $version" "public/$version" "$commit"
	say "tagged the private commit $version and the public commit public/$version"
}

push() {
	local refspecs=("refs/heads/$BRANCH:refs/heads/$REMOTE_BRANCH" "refs/tags/public/$version:refs/tags/$version")
	if ! git push --atomic "$REMOTE" "${refspecs[@]}"; then
		die "the push failed; the release is made here, so retry only the push: git push --atomic $REMOTE ${refspecs[*]}"
	fi
	say "pushed $version to $REMOTE; deploy it once CI is green: deploy/deploy.sh $version"
}

version=${1:-}
cd "$(git rev-parse --show-toplevel)"
preflight
checks
tree=$(public_tree)
scan "$tree"
release "$tree"
push
