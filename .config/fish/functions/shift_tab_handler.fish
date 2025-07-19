function shift_tab_handler
    # Try to go backward in menu (works if menu is open)
    # Otherwise, force open the completion menu
    if commandline --paging-mode
        commandline -f complete-and-search
    else
        commandline -f complete     # Open completion menu
    end
end
