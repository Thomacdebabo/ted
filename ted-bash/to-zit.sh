#!/bin/bash

ted-to-zit() {
    local file="$1"
    
    if [[ -z "$file" ]]; then
        echo "Usage: ted-to-zit <filepath>" >&2
        return 1
    fi
    
    if [[ ! -f "$file" ]]; then
        echo "File $file does not exist." >&2
        return 1
    fi
    
    # Parse YAML frontmatter and markdown content
    local in_frontmatter=false
    local todo_id=""
    local project_id=""
    local info=""
    local todo_name=""
    local goal=""
    local line_num=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Detect start of frontmatter
        if [[ $line_num -eq 1 && "$line" == "---" ]]; then
            in_frontmatter=true
            continue
        fi
        
        # Detect end of frontmatter
        if [[ "$in_frontmatter" == true && "$line" == "---" ]]; then
            in_frontmatter=false
            continue
        fi
        
        # Parse frontmatter fields
        if [[ "$in_frontmatter" == true ]]; then
            if [[ "$line" =~ ^id:[[:space:]]*(.*) ]]; then
                todo_id="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^project_id:[[:space:]]*(.*) ]]; then
                # Debug: show what we captured
                local raw_project="${BASH_REMATCH[1]}"
                
                # Try to extract the actual ID from [[ID]] format
                if [[ "$raw_project" =~ \[\[([^]]+)\]\] ]]; then
                    project_id="${BASH_REMATCH[1]}"
                else
                    project_id="$raw_project"
                fi
            elif [[ "$line" =~ ^info:[[:space:]]*(.*) ]]; then
                info="${BASH_REMATCH[1]}"
                # Remove quotes if present
                info="${info#\"}"
                info="${info%\"}"
            fi
        else
            # After frontmatter, parse name and goal
            if [[ -z "$todo_name" && "$line" =~ ^#[[:space:]](.+) ]]; then
                todo_name="${BASH_REMATCH[1]}"
                # Next line should be the goal
                read -r goal
                goal="${goal#"${goal%%[![:space:]]*}"}" # trim leading whitespace
                break
            fi
        fi
    done < "$file"
    local project_string="$project_id"
    if [[ -n "$project_id" ]]; then
        local project_file="$HOME/.ted/projects/${project_id}.md"
        if [[ -f "$project_file" ]]; then
            # Parse project file for shorthand and name
            local project_shorthand=""
            local project_name=""
            local in_proj_frontmatter=false
            local proj_line_num=0
            
            while IFS= read -r line; do
                ((proj_line_num++))
                
                if [[ $proj_line_num -eq 1 && "$line" == "---" ]]; then
                    in_proj_frontmatter=true
                    continue
                fi
                
                if [[ "$in_proj_frontmatter" == true && "$line" == "---" ]]; then
                    in_proj_frontmatter=false
                    continue
                fi
                
                if [[ "$in_proj_frontmatter" == false && "$line" =~ ^#[[:space:]](.+) ]]; then
                    local proj_title="${BASH_REMATCH[1]}"
                    # Check if format is "SHORTHAND: NAME"
                    if [[ "$proj_title" =~ ^([^:]+):[[:space:]]*(.+) ]]; then
                        project_shorthand="${BASH_REMATCH[1]}"
                        project_name="${BASH_REMATCH[2]}"
                    else
                        project_name="$proj_title"
                    fi
                    break
                fi
            done < "$project_file"
            
            if [[ -n "$project_shorthand" && -n "$project_name" ]]; then
                project_string="$project_shorthand - $project_name"
            fi
        fi
    fi
    
    # Format output similar to Python version
    # Output format: "PROJECT" -s "ID - NAME" -n "INFO"
    echo " \"${project_string}\" -s \"${todo_id} - ${todo_name}\" -n \"${info}\""
}