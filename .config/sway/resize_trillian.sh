#!/bin/bash

workspace=1
max_retries=15
retry_interval=2

for ((i=0; i<max_retries; i++)); do
    # Get sway tree
    tree=$(swaymsg -t get_tree)
    
    # Get workspace node (by name or number)
    ws_node=$(echo "$tree" | jq --arg ws "$workspace" '
    .. | select(type == "object" and .type == "workspace" and (.name == $ws or (.num == ($ws|tonumber)))) 
    ')

    # echo "Workspace node: $ws_node"
    
    # Count number of direct window children (ignore nested containers)
    window_count=$(echo "$ws_node" | jq '.nodes | length')
    
    if (( window_count >= 2 )); then
        # Get percent size of first (left) window
        left_width=$(echo "$ws_node" | jq '.nodes[0].geometry.width')
        full_width=$(echo "$ws_node" | jq '.rect.width')
        left_pct=$(echo "$left_width / $full_width" | bc -l)
        
        # Calculate right window percent = 1 - left_pct
        right_pct=$(echo "1 - $left_pct" | bc -l)
        right_pct_ppt=$(echo "$right_pct * 100" | bc | cut -d'.' -f1)
        
        # Focus right (index 1) window and resize it
        right_win_id=$(echo "$ws_node" | jq -r '.nodes[1].id')
        echo "Right window ID: $right_win_id"
        
        swaymsg "[con_id=$right_win_id]" focus
        swaymsg "resize set width ${right_pct_ppt} ppt"
        
        echo "Resized right window to $right_pct_ppt% width."
        exit 0
    fi
    
    echo "Windows not ready yet. Retry $((i+1))/$max_retries..."
    sleep $retry_interval
done

echo "Failed to find windows to resize after $max_retries retries."
exit 1
