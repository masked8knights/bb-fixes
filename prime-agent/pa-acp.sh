#!/bin/sh
# bb custom ACP agent shim for prime-agent (managed by bb-plugin-prime-agent-provider).
#   pa-acp.sh model-list            -> reformat `prime-agent model list` for bb's parser
#   pa-acp.sh <bb launch args...>   -> exec prime-agent, translating
#                                      `--model <provider>/<model>` into
#                                      `--model <model> --provider <provider>`
if [ "$1" = "model-list" ]; then
	shift
	# prime-agent prints the table to stderr (stdout is reserved); capture it
	# so the command status survives formatting and warnings stay out of stdout.
	tmp=$(mktemp "${TMPDIR:-/tmp}/prime-agent-model-list.XXXXXX") || exit 1
	trap 'rm -f "$tmp"' 0 HUP INT TERM
	prime-agent model list "$@" >"$tmp" 2>&1
	status=$?
	if [ "$status" -ne 0 ]; then
		cat "$tmp" >&2
		exit "$status"
	fi
	awk '
		function valid_provider(value) { return value ~ /^[[:alnum:]_.-]+$/ }
		function valid_model(value) { return value ~ /^[[:alnum:]_.@\/:+-]+$/ }
		tolower($1) == "provider" && tolower($2) == "model" { header=1; next }
		header && NF == 6 && valid_provider($1) && valid_model($2) {
			print $1 "/" $2 " - " $2 " (" $1 ")"
		}
	' "$tmp"
	exit $?
fi

out=""
prev_model=0
for a in "$@"; do
	if [ "$prev_model" = 1 ]; then
		case "$a" in
			*/*) p="${a%%/*}"; m="${a#*/}"; out="$out --model $m --provider $p" ;;
			*) out="$out --model $a" ;;
		esac
		prev_model=0
	elif [ "$a" = "--model" ]; then
		prev_model=1
	else
		out="$out $a"
	fi
done
# shellcheck disable=SC2086
exec prime-agent --continue $out
