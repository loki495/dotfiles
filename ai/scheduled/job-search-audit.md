Scheduled monthly run of the job search audit. Nobody is watching live; Andres reads the result later.

Read `~/dotfiles/ai/commands/job-search-audit.md` and follow it with no argument (all repos, résumé, profile README and LinkedIn), without `tools`. Its rules hold: edit no repo or résumé file, file nothing in Dibs until Andres has decided, launch workers as headless `sessioneer --mode auto` sessions and kill each once its report is read. Skip the audit and say so if `sessioneer --usage` shows the Claude session or weekly quota at 70% or more.

The run ends with the consolidated report as your final message (three-reader verdict first, then the priority list, mechanical items versus decisions, one batched decision list with a recommendation each). Write the two notes files as the command says. Do not fix anything.
