# Sleep refreshes both memory indexes and says how many (draft)

Two stores are filled by two commands: the memory link's drawer (`linkage warm`) and the semantic
search index (`find index`). A new exploration appears in one and not the other until a second
command is run. Sleep already has a memory-link refill phase that runs `warm()`.

Idea: the same phase also refreshes the search index for the explorations corpus, then records one
line with both counts: drawer items by source, and search chunks (with how many are new and how many
could not be embedded, so a run that embedded nothing cannot read clean).

- The path gathering and database location move from the CLI into `semantic_search`
  (`corpus_paths`, `default_db_path`, `default_repo_root`, `refresh_exploration_index`) so the
  command and sleep use one copy. The command's behaviour is unchanged.
- The drawer counts come from a small public function in the retriever that `linkage status` also
  uses, instead of two copies of the cache poking.
- Sleep resolves the explorations from the running checkout, like the drawer's own loader does.
- Letters are not added to the search index here; the job names explorations only.
