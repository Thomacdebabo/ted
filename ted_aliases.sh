alias tedit="obsidian://open?vault=.ted &"

# Source ted-bash functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/ted-bash/to-zit.sh" ]]; then
    source "$SCRIPT_DIR/ted-bash/to-zit.sh"
fi

fted() {
    local selected
    selected=$(find $HOME/.ted/todos/ -name "*.md" | sed "s|^$HOME/.ted/||" | fzf --preview="bat --color=always $HOME/.ted/{}")

    
    if [[ -n "$selected" ]]; then
        echo "$HOME/.ted/$selected"
    fi
}

ftedproj() {
    local selected
    selected=$(find $HOME/.ted/projects/ -name "*.md" | sed "s|^$HOME/.ted/projects||" | fzf --preview="bat --color=always $HOME/.ted/{}")

    
    if [[ -n "$selected" ]]; then
        echo "$HOME/.ted/projects/$selected"
    fi
}
nvted() {
  nvim $(fted)
}

tedc () {
  code $(fted)
}


upted() {
	ted update-file $(fted)
}

donted() {
	ted done-file $(fted)
}
sted() {
	ted show-file $(fted)
}

ted-id() {
  basename "$(fted)" | grep -oE '^[A-Z]+[0-9]+'
}

fzit() {
  zit start $(ted-id)
}

zted() {
  local time_flag=""
  if [[ -n "$1" ]]; then
    time_flag="-t $1"
  fi
  ted-to-zit "$(fted)" | xargs -I{} zit ted-start {} $time_flag
}

_find-next-id() {
    local dir=$1 # Use the provided directory
    local largest_id

    if [[ -z "$dir" ]]; then
        echo "Error: No directory provided."
        return 1
    fi

    largest_id=$(find "$dir" -name "*.md" 2>/dev/null | \
        grep -oE '[A-Z]+[0-9]+' | \
        grep -oE '[0-9]+' | \
        sed 's/^0*//' | \
        sort -n | \
        tail -1)

    if [[ -n "$largest_id" ]]; then
        echo $((largest_id + 1))
    else
        echo 0
    fi
}

next-todo-id() {
    local next_todo=$(_find-next-id "$HOME/.ted/todos/")
    local next_done=$(_find-next-id "$HOME/.ted/done/") 
    echo $(( next_todo > next_done ? next_todo : next_done )) 
}

next-project-id() {
    _find-next-id "$HOME/.ted/projects/"
}


#alias tedit="code ~/.ted &"

