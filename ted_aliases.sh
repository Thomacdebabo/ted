alias tedit="obsidian://open?vault=.ted &"

fted() {
    local selected
    selected=$(find $HOME/.ted/todos/ -name "*.md" | sed "s|^$HOME/.ted/||" | fzf --preview="bat --color=always $HOME/.ted/{}")

    
    if [[ -n "$selected" ]]; then
        echo "$HOME/.ted/$selected"
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


#alias tedit="code ~/.ted &"

