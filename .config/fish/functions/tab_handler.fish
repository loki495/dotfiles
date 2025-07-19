function tab_handler
    if commandline --paging-mode
        commandline -f complete
    else
        set autosuggestion (commandline -j)
        if test -n "$autosuggestion"
            commandline -f accept-autosuggestion
        else
            commandline -f complete
        end
    end
end
