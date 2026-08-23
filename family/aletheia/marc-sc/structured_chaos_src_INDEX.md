# src/ - Folder Index

This index maps the immediate contents of `src/` so it is easier to find the right file when something needs to change.

## Subfolders

| Folder | Purpose |
|---|---|
| `annotate/` | 12 immediate file(s). |
| `chatroom_client/` | 25 immediate file(s). |
| `config/` | 12 immediate file(s). |
| `firstrun/` | 3 immediate file(s). |
| `integrity/` | 2 immediate file(s). |
| `memory/` | 5 immediate file(s). |
| `pms_v2/` | 11 immediate file(s). |
| `shell/` | 3 immediate file(s). |

## Child Folder Rollup

| Folder | Index | Total Files | Indexed Files | Blocks |
|---|---|---:|---:|---:|
| `annotate/` | `annotate/_INDEX.md` | 12 | 11 | 143 |
| `chatroom_client/` | `chatroom_client/_INDEX.md` | 25 | 22 | 560 |
| `config/` | `config/_INDEX.md` | 12 | 8 | 80 |
| `firstrun/` | `firstrun/_INDEX.md` | 3 | 1 | 31 |
| `integrity/` | `integrity/_INDEX.md` | 2 | 1 | 13 |
| `memory/` | `memory/_INDEX.md` | 305 | 191 | 4074 |
| `pms_v2/` | `pms_v2/_INDEX.md` | 11 | 9 | 111 |
| `shell/` | `shell/_INDEX.md` | 3 | 1 | 14 |

## Files

| File | Lines | Purpose |
|---|---:|---|
| `__init__.py` | 0 | Package marker. |
| `chatroom_prompts.py` | 157 | Authoritative file-backed prompt surfaces for chatroom runtimes. |

## Block Map

Deterministic line ranges for indexed blocks under this folder, including child folders.

| Path | Block | Lines | Kind | Purpose |
|---|---|---:|---|---|
| `annotate/cache.py` | `put_cached` | 14-47 | function | Insert (or replace) an annotation cache entry. |
| `annotate/cache.py` | `get_all_for_file` | 50-77 | function | Return all cached annotations for a given file_sha256 and preset_id. |
| `annotate/cache.py` | `invalidate_file` | 80-95 | function | Delete all cached annotations for a given file_path. |
| `annotate/db.py` | `get_conn` | 194-207 | function | Open (and if needed initialise) data/annotations.db. |
| `annotate/db.py` | `_schema_meta_exists` | 210-215 | function | Return True if schema_meta table exists (fast check without catching errors). |
| `annotate/db.py` | `_table_columns` | 218-219 | function | Function block. |
| `annotate/db.py` | `_ensure_repo_slug_column` | 222-227 | function | Function block. |
| `annotate/db.py` | `ensure_schema` | 230-266 | function | Apply schema and any pending migrations. |
| `annotate/deps.py` | `_ext_to_language` | 66-68 | function | Function block. |
| `annotate/deps.py` | `_sha256` | 71-72 | function | Function block. |
| `annotate/deps.py` | `_is_process_preamble_summary` | 75-83 | function | Function block. |
| `annotate/deps.py` | `_path_to_file_uri` | 86-87 | function | Function block. |
| `annotate/deps.py` | `_file_uri_to_path` | 90-108 | function | Function block. |
| `annotate/deps.py` | `_decorate_definition_locations` | 111-139 | function | Add repo-relative jump metadata to definition locations inside the active repo. |
| `annotate/deps.py` | `_validate_and_extract_symbol` | 142-165 | function | Validate the (line, col) cursor against source and return the identifier under it (best-effort word at the cursor). |
| `annotate/deps.py` | `_get_cached_dep` | 172-203 | function | Function block. |
| `annotate/deps.py` | `_put_cached_dep` | 206-237 | function | Function block. |
| `annotate/deps.py` | `_build_dep_prompt` | 244-279 | function | Build the Opus prompt for describing dependency impact. |
| `annotate/deps.py` | `_call_opus` | 292-309 | async function | Run a strong-tier model call via the configured runner. |
| `annotate/deps.py` | `_english_for_refs` | 316-370 | async function | For each reference URI, return a cached English annotation for its block. |
| `annotate/deps.py` | `_lazy_annotate` | 373-378 | async function | Fire-and-forget: annotate a file in the background. |
| `annotate/deps.py` | `describe_deps` | 385-458 | async function | Return a plain-English description of what uses the symbol at (line, col). |
| `annotate/deps.py` | `describe_definition` | 461-499 | async function | Return the definition location(s) for the symbol at (line, col). |
| `annotate/lsp.py` | `LSPNotInstalled` | 50-55 | class | Raised when the required language server binary is not on PATH. |
| `annotate/lsp.py` | `LSPRequestError` | 58-59 | class | Raised when an installed language server cannot answer a request. |
| `annotate/lsp.py` | `_create_lsp_process` | 62-87 | async function | Async function block. |
| `annotate/lsp.py` | `_resolve_bin` | 90-110 | function | Return the full path to an npm-global binary. |
| `annotate/lsp.py` | `_path_to_file_uri` | 113-115 | function | Convert an absolute Path to a file:// URI, handling Windows drive letters. |
| `annotate/lsp.py` | `_file_uri_to_path` | 118-128 | function | Parse a file:// URI back to an absolute Path. |
| `annotate/lsp.py` | `_normalize_locations` | 131-154 | function | Normalize an LSP definition result into a flat list of {uri, range} dicts. |
| `annotate/lsp.py` | `LSPSidecar` | 157-537 | class | Single language server subprocess with full JSON-RPC lifecycle management. |
| `annotate/lsp.py` | `LSPSidecar.__init__` | 163-177 | method | Method block. |
| `annotate/lsp.py` | `LSPSidecar._next_id` | 183-185 | method | Method block. |
| `annotate/lsp.py` | `LSPSidecar._write` | 187-204 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._read_one` | 206-237 | async method | Read a single LSP message from stdout. |
| `annotate/lsp.py` | `LSPSidecar._reader_loop` | 243-269 | async method | Background task: read messages, route responses to waiting futures. |
| `annotate/lsp.py` | `LSPSidecar._handle_notification` | 271-278 | method | Method block. |
| `annotate/lsp.py` | `LSPSidecar._fail_pending` | 280-284 | method | Method block. |
| `annotate/lsp.py` | `LSPSidecar._request` | 290-300 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._notify` | 302-303 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._wait_for_document_ready` | 305-317 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._spawn` | 323-345 | async method | Spawn the language server subprocess and run the LSP handshake. |
| `annotate/lsp.py` | `LSPSidecar._do_initialize` | 347-367 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._ensure_running` | 369-385 | async method | Spawn (or restart) if the process is not alive. |
| `annotate/lsp.py` | `LSPSidecar._process_returncode` | 387-393 | method | Method block. |
| `annotate/lsp.py` | `LSPSidecar._wait_process` | 395-401 | async method | Async method block. |
| `annotate/lsp.py` | `LSPSidecar._open_and_wait_ready` | 407-449 | async method | Ensure the server is running, the document is opened once, and give diagnostics readiness a short grace window. |
| `annotate/lsp.py` | `LSPSidecar.find_references` | 451-482 | async method | Return LSP reference locations for the symbol at (line, col). |
| `annotate/lsp.py` | `LSPSidecar.find_definition` | 484-516 | async method | Return LSP definition locations for the symbol at (line, col). |
| `annotate/lsp.py` | `LSPSidecar.shutdown` | 518-537 | async method | Graceful shutdown: send shutdown+exit, then terminate. |
| `annotate/lsp.py` | `LSPManager` | 540-603 | class | Module-level registry: one LSPSidecar per language, shared across requests. |
| `annotate/lsp.py` | `LSPManager.__init__` | 547-549 | method | Method block. |
| `annotate/lsp.py` | `LSPManager._get_or_create` | 551-554 | method | Method block. |
| `annotate/lsp.py` | `LSPManager.find_references` | 556-574 | async method | Find all references for the symbol at the given position. |
| `annotate/lsp.py` | `LSPManager.find_definition` | 576-594 | async method | Find the definition location(s) for the symbol at the given position. |
| `annotate/lsp.py` | `LSPManager.shutdown_all` | 596-603 | async method | Shut down all sidecars. |
| `annotate/lsp.py` | `get_lsp_manager` | 610-615 | function | Return the shared LSPManager instance, creating it on first call. |
| `annotate/narrator.py` | `NarrationResult` | 36-39 | class | Class block. |
| `annotate/narrator.py` | `_build_batch_prompt` | 42-73 | function | Function block. |
| `annotate/narrator.py` | `_parse_batch_response` | 76-115 | function | Parse BLOCK_N sections from the response and mark missing blocks as failed. |
| `annotate/narrator.py` | `narrate_blocks_batch` | 118-158 | async function | Narrate all blocks in a single model-runner call. |
| `annotate/narrator.py` | `_build_line_by_line_prompt` | 169-194 | function | Function block. |
| `annotate/narrator.py` | `_parse_line_by_line_response` | 197-225 | function | Function block. |
| `annotate/narrator.py` | `narrate_lines` | 228-260 | async function | Line-by-line explanation for a single code block. |
| `annotate/parser.py` | `Block` | 42-47 | class | Class block. |
| `annotate/parser.py` | `parse_blocks` | 54-75 | function | Parse source into annotatable blocks. |
| `annotate/parser.py` | `_block_hash` | 82-83 | function | Function block. |
| `annotate/parser.py` | `_node_text` | 86-87 | function | Function block. |
| `annotate/parser.py` | `_make_block` | 90-98 | function | Function block. |
| `annotate/parser.py` | `_make_text_block` | 101-109 | function | Function block. |
| `annotate/parser.py` | `_line_starts` | 112-116 | function | Function block. |
| `annotate/parser.py` | `_offset_to_line` | 119-128 | function | Function block. |
| `annotate/parser.py` | `_collapse_imports` | 131-173 | function | Merge consecutive import blocks that are adjacent (no gap between them). |
| `annotate/parser.py` | `_parse_python` | 190-210 | function | Function block. |
| `annotate/parser.py` | `_py_class_node` | 213-221 | function | Return the class_definition node if `node` is a class or a decorated class, else None. |
| `annotate/parser.py` | `_py_split_class` | 224-274 | function | Split a Python class into: - a class-header block (decorators + class signature + class docstring, ending just before the first method) - one block per function_definition or decorated_definition inside the body Class-level statements that are not functions (e.g. |
| `annotate/parser.py` | `_parse_js` | 293-313 | function | Function block. |
| `annotate/parser.py` | `_js_class_node` | 316-325 | function | Return the class_declaration node if this is a class or wraps one, else None. |
| `annotate/parser.py` | `_js_split_class` | 328-363 | function | JS class → header block + per-method blocks. |
| `annotate/parser.py` | `_parse_html` | 387-453 | function | Parse HTML into line-aware structural blocks. |
| `annotate/parser.py` | `_dedupe_contained_html_blocks` | 456-468 | function | Function block. |
| `annotate/parser.py` | `_remove_html_container_blocks` | 471-499 | function | Keep non-overlapping HTML blocks for the Codebase interleaved renderer. |
| `annotate/pipeline.py` | `_file_sha256` | 29-30 | function | Function block. |
| `annotate/pipeline.py` | `_language_from_path` | 33-44 | function | Function block. |
| `annotate/pipeline.py` | `annotate_file` | 47-154 | async function | Annotate all blocks in the given file. |
| `annotate/rewriter.py` | `_language_from_path` | 41-51 | function | Function block. |
| `annotate/rewriter.py` | `_find_block_by_hash` | 54-58 | function | Function block. |
| `annotate/rewriter.py` | `_file_sha256` | 61-62 | function | Function block. |
| `annotate/rewriter.py` | `_build_regen_prompt` | 65-94 | function | Function block. |
| `annotate/rewriter.py` | `_strip_fences` | 97-104 | function | Remove markdown code fences if Opus added them despite instructions. |
| `annotate/rewriter.py` | `_run_claude` | 107-128 | async function | Run a strong-tier model call via the configured runner. |
| `annotate/rewriter.py` | `_git_stage` | 131-144 | async function | Stage the file with git add (relative path from repo root). |
| `annotate/rewriter.py` | `regen_block` | 147-183 | async function | Regen a block using Opus. |
| `annotate/rewriter.py` | `apply_block` | 186-240 | async function | Replace a block in the file on disk, invalidate annotation cache, git stage. |
| `annotate/routes.py` | `_language_for` | 76-82 | function | Delegate to the canonical language map shared with the codebase API. |
| `annotate/routes.py` | `_file_sha256` | 85-86 | function | Function block. |
| `annotate/routes.py` | `_http_exception_detail` | 89-102 | function | Function block. |
| `annotate/routes.py` | `_encoding_hidden_path` | 105-107 | function | Function block. |
| `annotate/routes.py` | `_encoding_auto_repair_allowed` | 110-113 | function | Function block. |
| `annotate/routes.py` | `_active_annotation_preset` | 116-135 | function | Return the active annotation preset id and prompt, falling back to default. |
| `annotate/routes.py` | `_matches_optional_glob` | 138-142 | function | Function block. |
| `annotate/routes.py` | `_is_excluded_search_dir` | 145-149 | function | Function block. |
| `annotate/routes.py` | `_filename_search_results` | 152-204 | function | Function block. |
| `annotate/routes.py` | `_unified_diff` | 207-216 | function | Function block. |
| `annotate/routes.py` | `_diff_history_index` | 219-253 | function | Return diff-history counts keyed by repo-relative file path. |
| `annotate/routes.py` | `_diff_history_for_entry` | 256-293 | function | Function block. |
| `annotate/routes.py` | `_workspace_tree_display_name` | 296-313 | function | Function block. |
| `annotate/routes.py` | `_normalize_rel_path` | 316-317 | function | Function block. |
| `annotate/routes.py` | `_workspace_runtime_allowed` | 320-327 | function | Function block. |
| `annotate/routes.py` | `_workspace_runtime_root` | 330-342 | function | Function block. |
| `annotate/routes.py` | `_workspace_runtime_match` | 345-364 | function | Function block. |
| `annotate/routes.py` | `_resolve_workspace_runtime_path` | 367-383 | function | Function block. |
| `annotate/routes.py` | `_workspace_runtime_mount_entry` | 386-397 | function | Function block. |
| `annotate/routes.py` | `_workspace_runtime_tree_entries` | 400-417 | function | Function block. |
| `annotate/routes.py` | `search_codebase` | 425-534 | async function | Search repo text with ripgrep, scoped to the annotate whitelist. |
| `annotate/routes.py` | `get_tree` | 542-623 | async function | Return directory listing for `path` relative to repo root. |
| `annotate/routes.py` | `get_file` | 631-681 | async function | Return file content, sha256, and detected language. |
| `annotate/routes.py` | `SaveFileRequest` | 684-690 | class | Class block. |
| `annotate/routes.py` | `save_file` | 694-784 | async function | Full-file save from the Codebase editor; emits the same durable file_diff event. |
| `annotate/routes.py` | `get_file_annotations` | 794-847 | async function | Return block-level English annotations for a file. |
| `annotate/routes.py` | `get_cached_file_annotations` | 855-913 | async function | Return only already-cached block annotations for a file. |
| `annotate/routes.py` | `get_presets` | 921-932 | async function | Return all annotation presets. |
| `annotate/routes.py` | `CreatePresetRequest` | 939-942 | class | Class block. |
| `annotate/routes.py` | `create_preset` | 946-966 | async function | Create a custom annotation preset. |
| `annotate/routes.py` | `get_active_preset` | 974-987 | async function | Return the currently active preset. |
| `annotate/routes.py` | `SetActivePresetRequest` | 994-995 | class | Class block. |
| `annotate/routes.py` | `set_active_preset` | 999-1025 | async function | Set the active preset by id. |
| `annotate/routes.py` | `RegenBlockRequest` | 1032-1037 | class | Class block. |
| `annotate/routes.py` | `post_regen_block` | 1041-1065 | async function | Given a block hash and new English description, regenerate the code block using Opus with full file context. |
| `annotate/routes.py` | `ApplyBlockRequest` | 1072-1076 | class | Class block. |
| `annotate/routes.py` | `post_apply_block` | 1080-1139 | async function | Write new_code into the file at the block's line range, invalidate the annotation cache for that file, and git stage the change. |
| `annotate/routes.py` | `get_block_lines` | 1147-1206 | async function | Line-by-line explanation for a single code block. |
| `annotate/routes.py` | `get_deps` | 1214-1245 | async function | Return a plain-English description of what uses the symbol at (path, line, col). |
| `annotate/routes.py` | `get_definition` | 1253-1285 | async function | Return the definition location(s) for the symbol at (path, line, col). |
| `annotate/routes.py` | `get_file_summary` | 1293-1396 | async function | Return a one-liner English summary of what the file does. |
| `annotate/routes.py` | `get_dir_summary` | 1404-1473 | async function | Return a short description of what a directory contains. |
| `annotate/routes.py` | `encoding_scan` | 1482-1594 | async function | Scan repo for encoding artifacts. |
| `annotate/routes.py` | `EncodingRepairRequest` | 1601-1604 | class | Class block. |
| `annotate/routes.py` | `encoding_repair` | 1608-1674 | async function | Apply selective mojibake recovery to a single file. |
| `annotate/summarizer.py` | `summarize_file` | 28-61 | async function | Given a filename and its block-level English descriptions, return a one-liner. |
| `annotate/whitelist.py` | `is_allowed` | 36-46 | function | Return False if rel_path matches any excluded pattern. |
| `annotate/whitelist.py` | `resolve_safe` | 49-70 | function | Resolve rel_path against the given root (defaults to REPO_ROOT) safely. |
| `annotate/whitelist.py` | `resolve_root_for_slug` | 73-88 | function | Return the repo root for a given slug. |
| `chatroom_client/api_server.py` | `_load_index` | 27-33 | function | Function block. |
| `chatroom_client/api_server.py` | `_save_index` | 36-37 | function | Function block. |
| `chatroom_client/api_server.py` | `health` | 41-42 | async function | Async function block. |
| `chatroom_client/api_server.py` | `list_files` | 46-47 | async function | Async function block. |
| `chatroom_client/api_server.py` | `upload_files` | 51-74 | async function | Async function block. |
| `chatroom_client/api_server.py` | `get_file` | 78-86 | async function | Async function block. |
| `chatroom_client/api_server.py` | `run_server` | 89-112 | async function | Start uvicorn in-process. |
| `chatroom_client/collab_modes.py` | `_slug` | 14-17 | function | Character-name → filesystem slug: lowercase alphanumerics joined by underscores. |
| `chatroom_client/collab_modes.py` | `_mode_prompt_path` | 20-21 | function | Function block. |
| `chatroom_client/collab_modes.py` | `_overlay_prompt_path` | 24-25 | function | Function block. |
| `chatroom_client/collab_modes.py` | `_slot_for_ai_id` | 28-34 | function | Function block. |
| `chatroom_client/collab_modes.py` | `_selfie_context` | 37-43 | function | Function block. |
| `chatroom_client/collab_modes.py` | `_catalog` | 46-47 | function | Function block. |
| `chatroom_client/collab_modes.py` | `get_mode` | 54-56 | function | Return mode definition dict or None if unknown. |
| `chatroom_client/collab_modes.py` | `valid_mode_ids` | 59-61 | function | Return the current editable mode ids. |
| `chatroom_client/collab_modes.py` | `normalize_mode_id` | 64-67 | function | Return mode_id if it exists in the editable catalog, otherwise default. |
| `chatroom_client/collab_modes.py` | `get_profile` | 70-92 | function | Get the system prompt suffix for a given mode and AI slot ("ai1"/"ai2"). |
| `chatroom_client/collab_modes.py` | `display_name_for_participant` | 95-103 | function | Resolve Muse/Anvil participant ids to the current mode character names. |
| `chatroom_client/collab_modes.py` | `mode_list_for_ui` | 106-119 | function | Return mode list suitable for JSON response (excludes prompt text). |
| `chatroom_client/help_prompt_package.py` | `_workspace_file` | 18-19 | function | Function block. |
| `chatroom_client/help_prompt_package.py` | `_read_required` | 22-26 | function | Function block. |
| `chatroom_client/help_prompt_package.py` | `_markdown_section` | 29-40 | function | Function block. |
| `chatroom_client/help_prompt_package.py` | `_text_fence` | 43-50 | function | Function block. |
| `chatroom_client/help_prompt_package.py` | `_agent_wrapper_heading` | 53-59 | function | Function block. |
| `chatroom_client/help_prompt_package.py` | `build_help_room_prompt_block` | 62-96 | function | Return HELP-room instructions for Anvil/Muse, or empty for other agents. |
| `chatroom_client/helpers.py` | `_activity_metadata` | 25-28 | function | Function block. |
| `chatroom_client/helpers.py` | `_test_telemetry_disabled` | 31-35 | function | Function block. |
| `chatroom_client/helpers.py` | `sync_http_get` | 48-52 | function | Blocking HTTP GET that returns parsed JSON. |
| `chatroom_client/helpers.py` | `sync_http_post` | 55-59 | function | Blocking HTTP POST with JSON body. |
| `chatroom_client/helpers.py` | `send_reaction` | 62-70 | function | POST a reaction to a chatroom message. |
| `chatroom_client/helpers.py` | `post_thinking_indicator` | 75-96 | function | POST a thinking-type message to the chatroom for the chat UI. |
| `chatroom_client/helpers.py` | `_snapshot_key` | 99-100 | function | Function block. |
| `chatroom_client/helpers.py` | `_project_relative_path` | 103-107 | function | Function block. |
| `chatroom_client/helpers.py` | `_display_path` | 110-112 | function | Function block. |
| `chatroom_client/helpers.py` | `_normalize_diff_text` | 115-116 | function | Function block. |
| `chatroom_client/helpers.py` | `_resolve_diff_file_path` | 119-150 | function | Function block. |
| `chatroom_client/helpers.py` | `_get_git_head_content` | 153-165 | function | Return file content at git HEAD, or empty string if not tracked. |
| `chatroom_client/helpers.py` | `snapshot_file_diff_baseline` | 168-178 | function | Remember file content before an edit tool runs. |
| `chatroom_client/helpers.py` | `post_file_diff_event` | 181-212 | function | Read file after an Edit/Write, diff against snapshot, emit file_diff event. |
| `chatroom_client/helpers.py` | `compute_file_diff_body` | 215-249 | function | Compute the unified diff body for file against its snapshot (or git head). |
| `chatroom_client/helpers.py` | `post_file_diff_body_event` | 252-284 | function | Emit a file_diff event from an already-known unified diff. |
| `chatroom_client/helpers.py` | `post_activity_event` | 287-312 | function | Fire-and-forget activity event to the API. |
| `chatroom_client/helpers.py` | `post_ai_seen_receipt` | 315-354 | function | Post UI-only AI receipt state for messages the subprocess actually saw. |
| `chatroom_client/helpers.py` | `extract_assistant_text` | 357-363 | function | Extract text from a claude -p assistant stream-json entry. |
| `chatroom_client/helpers.py` | `describe_tool_use` | 366-409 | function | Map a tool_use content block to a human-readable thinking label. |
| `chatroom_client/helpers.py` | `_post_plan_to_chatroom` | 412-440 | async function | Post a plan to the chatroom Actions tab for approval and return the message id when available. |
| `chatroom_client/helpers.py` | `_codebase_scope_prompt_block` | 443-477 | function | Function block. |
| `chatroom_client/helpers.py` | `_build_system_prompt` | 480-516 | function | Build system prompt with fresh timestamp. |
| `chatroom_client/main.py` | `_last_seen_state_key` | 39-41 | function | Function block. |
| `chatroom_client/main.py` | `_load_last_seen_id` | 44-59 | function | Load persisted last-seen message ID for gap recovery on reconnect. |
| `chatroom_client/main.py` | `_save_last_seen_id` | 62-73 | function | Persist the last-seen message ID so reconnects can request gap replay. |
| `chatroom_client/main.py` | `_ssl_context_for` | 76-102 | function | SSL context for the chatroom WebSocket. |
| `chatroom_client/main.py` | `_build_ws_url` | 105-128 | function | Function block. |
| `chatroom_client/main.py` | `_agent_http_base` | 131-133 | function | Local API side-channel for agent HTTP chores; never derived from public WSS. |
| `chatroom_client/main.py` | `_normalize_connect_event` | 166-170 | function | Function block. |
| `chatroom_client/main.py` | `_current_restart_marker_event` | 173-199 | function | Function block. |
| `chatroom_client/main.py` | `_should_emit_api_reconnect_wake` | 202-204 | function | Function block. |
| `chatroom_client/main.py` | `parse_args` | 210-221 | function | Function block. |
| `chatroom_client/main.py` | `_graceful_shutdown` | 227-267 | async function | Clean shutdown sequence. |
| `chatroom_client/main.py` | `_async_main` | 273-749 | async function | Async function block. |
| `chatroom_client/main.py` | `main` | 755-766 | function | Function block. |
| `chatroom_client/models.py` | `ChatMessage` | 19-53 | class | Class block. |
| `chatroom_client/models.py` | `ChatMessage.from_dict` | 36-39 | method | Create from dict, ignoring unknown fields (server may add new ones). |
| `chatroom_client/models.py` | `ChatMessage.mentions_us` | 41-44 | method | True if this message @mentions our participant or @all. |
| `chatroom_client/models.py` | `ChatMessage.is_human` | 46-47 | method | Method block. |
| `chatroom_client/models.py` | `ChatMessage.is_collab` | 49-50 | method | Method block. |
| `chatroom_client/models.py` | `ChatMessage.is_from_us` | 52-53 | method | Method block. |
| `chatroom_client/models.py` | `is_ai_receiptable_message` | 75-88 | function | True when an AI seeing this message should tick the visible receipt. |
| `chatroom_client/models.py` | `ai_receipt_message_ids` | 91-102 | function | Function block. |
| `chatroom_client/models.py` | `is_agent_visible_msg_type` | 105-114 | function | True if msg's type is real conversation/actionable-event content for an agent (i.e. |
| `chatroom_client/models.py` | `is_agent_context_message` | 117-127 | function | True if msg belongs in an agent's wake-catchup context. |
| `chatroom_client/monitor_reporter.py` | `_normalize_room_id` | 51-52 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_fetch_server_model_effort` | 55-76 | function | Read model/effort from Mac's /chatroom/status. |
| `chatroom_client/monitor_reporter.py` | `_fetch_recent_activity_ts` | 79-101 | function | Return the newest activity timestamp for an agent from the API feed. |
| `chatroom_client/monitor_reporter.py` | `_ts` | 104-108 | function | Convert epoch float to ISO 8601 string or None. |
| `chatroom_client/monitor_reporter.py` | `_build_subprocess_info` | 111-149 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_get_orchestrator_state` | 153-194 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_get_thinker_state` | 197-241 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_workspace_process_slug` | 244-245 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_read_int_file` | 248-252 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_curator_stats_path` | 255-259 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_curator_log_path` | 262-266 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_curator_pid_path` | 269-273 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_pid_belongs_to_curator_room` | 276-291 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_live_descendant_pid` | 294-319 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_read_monitor_stats` | 322-332 | function | Read a monitor stats JSON file written by a standalone subprocess. |
| `chatroom_client/monitor_reporter.py` | `_get_curator_state` | 335-418 | function | Memory Curator, reported from the exact room-scoped supervisor. |
| `chatroom_client/monitor_reporter.py` | `_parse_iso` | 438-445 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_v2_primary_runtime_enabled` | 448-449 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_task_stat` | 452-458 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_pms_v2_live_processing_state` | 461-532 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_get_governance_task_state` | 535-586 | function | Build the legacy Record Extraction Monitor row from cumulative stats. |
| `chatroom_client/monitor_reporter.py` | `_get_all_governance_task_states` | 595-606 | function | Return one Monitor row per registered governance task. |
| `chatroom_client/monitor_reporter.py` | `_fetch_health_snapshot` | 616-623 | function | Read /health from the local API for restart time + connection count. |
| `chatroom_client/monitor_reporter.py` | `_get_api_connections_state` | 626-659 | function | API process uptime (since last restart) + live chatroom websocket count. |
| `chatroom_client/monitor_reporter.py` | `_backup_dest_root` | 662-664 | function | Function block. |
| `chatroom_client/monitor_reporter.py` | `_get_backups_state` | 667-712 | function | Verify the daily PMS backup rotation (3-day rolling retention). |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter` | 716-813 | class | Event-driven reporter. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter.__init__` | 719-728 | method | Method block. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter.notify` | 730-740 | method | Signal that something changed. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter.start` | 742-747 | method | Launch the background reporter task. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter._run` | 749-762 | async method | Async method block. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter._handle_change` | 764-778 | async method | Async method block. |
| `chatroom_client/monitor_reporter.py` | `MonitorReporter._send_report` | 780-813 | async method | Async method block. |
| `chatroom_client/monitor_reporter.py` | `_post_report` | 817-829 | function | Synchronous HTTP POST to Mac monitor endpoint. |
| `chatroom_client/orchestrator_hot_memory.py` | `_hot_memory_section` | 108-129 | function | Return only the HOT lane from a HOT source file. |
| `chatroom_client/orchestrator_hot_memory.py` | `_hash_text` | 132-133 | function | Function block. |
| `chatroom_client/orchestrator_hot_memory.py` | `_is_main_room` | 136-138 | function | Function block. |
| `chatroom_client/orchestrator_hot_memory.py` | `_workspace_overview_has_items` | 141-142 | function | Function block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader` | 145-783 | class | Owns HOT/FRAMING/feedback context reads for one orchestrator. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.__init__` | 148-149 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.wake_context_blocks` | 153-188 | async method | Build shared context blocks before any wake prompt is assembled. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.hot_memory_block` | 190-192 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.authority_files_block` | 194-209 | method | Return harness authority files for post-compaction rehydration. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._authority_paths_for_current_harness` | 211-224 | method | Return only the authority-file family for the active harness. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._check_and_queue_pending_lanes` | 226-252 | method | Mark lanes as pending when their cadence threshold is met. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.mark_hot_updated` | 254-261 | method | Queue HOT first for SILENT-gated delivery after a Curator HOT write. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.has_pending_context_lanes` | 263-265 | method | True if any context lanes are due and waiting for a SILENT drain. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.pop_pending_context_lane` | 267-369 | method | Read and return the next pending lane's content. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.hot_memory_block_with_meta` | 371-382 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._build_full_context_bundle` | 384-481 | method | Build and return all context lanes together (spawn/force path). |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.emit_hot_memory_debug` | 483-522 | async method | Async method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader.emit_feedback_calibration_debug` | 524-540 | async method | Async method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_dynamic_nudge` | 544-556 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._is_collab_present` | 558-583 | method | True when a guest is active in this room (the clean-floor trigger). |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._repo_path` | 585-586 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_text_file` | 588-594 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_lane_file` | 596-597 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_agent_rules` | 599-606 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_room_context` | 608-629 | method | Read the room-scoped Room Context lane (user-defined personal/company context). |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_personality` | 631-639 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_hot_memory` | 641-642 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._read_workspace_hot_overview` | 644-654 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._workspace_hot_entries` | 656-663 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._seed_workspace_hot_delta_state` | 665-674 | method | Treat current workspace SHORT entries as already known for this PID. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._workspace_hot_delta_ready` | 676-710 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._pop_workspace_hot_delta` | 712-757 | method | Method block. |
| `chatroom_client/orchestrator_hot_memory.py` | `HotMemoryReader._feedback_calibration_block` | 759-783 | async method | Fetch short-lived feedback calibration for this agent. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager` | 24-106 | class | Owns the idle nudge file-watch loop for one orchestrator. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager.__init__` | 27-30 | method | Method block. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager._read_idle_nudge` | 32-49 | method | Read the server-written mode idle-nudge file for this participant. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager.idle_loop` | 51-71 | async method | Poll the server-written idle-nudge file; inject as a wake when fresh. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager._clear_idle_nudge` | 73-92 | async method | Async method block. |
| `chatroom_client/orchestrator_nudges.py` | `NudgeManager._queue_idle_nudge` | 94-106 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `is_auth_error` | 87-89 | function | Function block. |
| `chatroom_client/orchestrator_output_filter.py` | `is_rate_limit_error` | 92-94 | function | Function block. |
| `chatroom_client/orchestrator_output_filter.py` | `is_overload_error` | 97-99 | function | Function block. |
| `chatroom_client/orchestrator_output_filter.py` | `_lease_timestamp_age_seconds` | 102-118 | function | Seconds between `value` (a plan_items-style ISO timestamp, e.g. |
| `chatroom_client/orchestrator_output_filter.py` | `is_image_limit_error` | 121-123 | function | Function block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter` | 126-1300 | class | Own outbound text filtering, CLAIM handling, and buffer decisions. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.__init__` | 129-130 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.send_text_block` | 132-289 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.send_silent_decision` | 291-362 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.send_empty_silence` | 364-369 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._drain_pending_context_lane` | 371-401 | async method | After SILENT, pop one pending context lane and enqueue a refresh wake. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.cancel_pending_claim_continuation_if_turn_continued` | 403-417 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.send_buffer_decision` | 419-496 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.scan_output_tokens` | 498-499 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.parse_buffer_decision` | 501-502 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.normalize_outbound_text` | 504-505 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_register_claim` | 507-537 | method | POST to shared claim registry. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_image_complaint` | 539-540 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_auth_error` | 542-543 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_rate_limit_error` | 545-546 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_overload_error` | 548-549 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_image_limit_error` | 551-552 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_filler` | 554-560 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_self_review_complete` | 563-567 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_doc_check_complete` | 570-574 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_doc_review_complete` | 577-581 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.hash_text` | 583-584 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.is_duplicate_visible_send` | 586-595 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.remember_visible_send` | 597-600 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.write_block_until_steer` | 602-614 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.clear_block_until_steer` | 616-624 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._handle_standalone_claim` | 626-691 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._handle_pending_claim` | 693-732 | async method | New protocol: a standalone [CLAIM:] proposes a pending queue item. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._handle_pending_claims` | 734-774 | async method | New protocol (multi-claim): stage one or more standalone [CLAIM:] lines as independent pending queue items. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._handle_claim_started` | 776-874 | async method | New protocol: [CLAIM STARTED:] opens execution, but only against a real server lease for THIS agent. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_create_claim_queue_item` | 876-907 | method | POST a pending item to the Claims queue. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_create_plan_item` | 909-911 | method | Compatibility shim for older tests/extensions. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_find_my_lease` | 913-936 | method | Confirm a leased/running queue item with this label is assigned to this agent. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_room_has_fresh_peer_claim` | 938-966 | method | True if some OTHER agent holds a leased/running claims-queue item in this room whose lease was refreshed within PEER_CLAIM_FRESHNESS_SECONDS. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_self_lease` | 968-1020 | method | Auto Pick-Up Option B self-lease: with no pre-granted lease, the agent that posted [CLAIM STARTED:] leases the matching PENDING queue item to itself. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_mark_plan_item_running` | 1022-1037 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_heartbeat_plan_item` | 1039-1056 | method | Re-arm the lease for an actively-running claim. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._claim_heartbeat_loop` | 1058-1072 | async method | While THIS claim is the agent's active claim, periodically re-arm its lease so a long (multi-minute) claim is never reaped mid-execution. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._start_claim_heartbeat` | 1074-1080 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._stop_claim_heartbeat` | 1082-1086 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter.api_complete_plan_item` | 1088-1103 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._mark_plan_item_running` | 1105-1113 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._complete_plan_item_for_claim` | 1115-1160 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._extract_claim_complete_label` | 1163-1165 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._normalize_noop_reason` | 1168-1171 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._extract_noop_claim_close` | 1173-1215 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._validated_noop_claim_close` | 1217-1250 | async method | Async method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._current_git_head` | 1252-1264 | method | Method block. |
| `chatroom_client/orchestrator_output_filter.py` | `OutputFilter._handle_blocked_claim` | 1266-1300 | async method | Async method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `_att_is_image` | 59-66 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `_att_key` | 69-76 | function | Dedup/identity key for an attachment. |
| `chatroom_client/orchestrator_prompt_builder.py` | `_att_upload_ref` | 79-86 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `_att_disk_path` | 89-100 | function | Resolve an attachment to its on-disk transfers path, or None. |
| `chatroom_client/orchestrator_prompt_builder.py` | `prompt_block` | 103-108 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `protect_template_literals` | 115-117 | function | Keep authored {{TOKEN}} text inert while the prompt shell renders. |
| `chatroom_client/orchestrator_prompt_builder.py` | `restore_template_literals` | 120-121 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `sc_block` | 124-135 | function | Wrap injected dynamic context in an assembler-owned visible envelope. |
| `chatroom_client/orchestrator_prompt_builder.py` | `normalize_rendered_wake_prompt` | 138-150 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `format_ts` | 153-160 | function | Extract HH:MM:SS from message timestamp for prompt context. |
| `chatroom_client/orchestrator_prompt_builder.py` | `format_visible_message_id` | 163-164 | function | Function block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder` | 167-875 | class | Owns wake prompt assembly for one orchestrator. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.__init__` | 170-176 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.runtime_prompt` | 180-182 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.wake_prompt` | 184-186 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_wake_guidance_block` | 188-191 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.render_wake_prompt` | 193-199 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.room_context_block` | 201-217 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.format_message_batch` | 221-292 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.catchup_lines` | 294-309 | method | Format a "since you last saw the room" block from missed messages. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.active_claim_warning` | 311-347 | method | Return a warning block if any missed message contains [CLAIM:] from another agent. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.missed_excluding_current` | 349-370 | method | Drop messages already rendered in the designated current block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder._mark_image_inlined` | 372-392 | method | Record that this image attachment was inlined as vision bytes. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.collect_attachments` | 394-409 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.collect_missed_attachments` | 411-448 | method | Re-inline recent attachments from catchup (missed) messages. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder._inlined_image_keys` | 450-462 | method | Keys of image attachments that will be injected as bytes this wake. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_direct_wake_prompt` | 466-490 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder._build_context_wake_prompt` | 492-545 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_collab_join_wake_prompt` | 547-562 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_peer_wake_prompt` | 564-582 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_api_reconnect_prompt` | 584-610 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_tagged_wake_prompt` | 612-668 | method | Method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_buffer_revise_prompt` | 670-695 | method | Build the fresh-decision wake prompt: standard wake context + buffer decision rules. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_context_refresh_prompt` | 697-706 | method | Build a minimal prompt for a SILENT-gated context lane refresh. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.build_startup_context_prompt` | 708-768 | async method | Async method block. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.consume_respawn_banner` | 772-817 | method | Return the respawn banner text if the first-wake flag is set, then clear. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.consume_control_notices` | 819-828 | method | Read and clear one-shot control notices written by the chatroom server. |
| `chatroom_client/orchestrator_prompt_builder.py` | `WakePromptBuilder.consume_notice_blocks` | 830-875 | method | Read and clear one-shot notice files, split by prompt block type. |
| `chatroom_client/orchestrator_stream.py` | `diff_file_paths_for_tool` | 27-34 | function | Function block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler` | 37-483 | class | Own partial-stream state for one orchestrator instance. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.__init__` | 40-48 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._claim_diff_metadata` | 50-64 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.flush_live_text_buffer` | 66-90 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_stream_event` | 92-103 | async method | Forward partial-message stream events to the Activity panel. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_file_diff_entry` | 105-116 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_file_diff_preview_entry` | 118-130 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_file_diff_preview_clear_entry` | 132-143 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_tool_result_entry` | 145-183 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.handle_assistant_entry` | 185-201 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler.reset_for_result` | 203-210 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._emit_tool_start_once` | 212-218 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._handle_content_block_start` | 220-250 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._handle_content_block_delta` | 252-281 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._handle_content_block_stop` | 283-303 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._handle_assistant_text` | 305-351 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._cut_off_for_pending_soft_interrupt` | 353-373 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._record_assistant_tool_use` | 375-398 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._track_diff_tool` | 400-427 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._deferred_file_diff_check` | 429-461 | async method | Async method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._tool_result_text` | 464-471 | method | Method block. |
| `chatroom_client/orchestrator_stream.py` | `StreamEventHandler._write_diag_stream` | 473-483 | method | Method block. |
| `chatroom_client/orchestrator_turn_state.py` | `TurnState` | 24-51 | class | Class block. |
| `chatroom_client/orchestrator_v2.py` | `_owned_pids_path` | 135-136 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_read_owned_pids` | 139-148 | function | Return the live SC-owned PID registry as {pid_str: {...}}. |
| `chatroom_client/orchestrator_v2.py` | `_register_owned_pid` | 151-167 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_deregister_owned_pid` | 170-181 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_sc_killed_pids_path` | 184-185 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_mark_sc_killed_pid` | 188-212 | function | Record that an SC actor is about to kill `pid`. |
| `chatroom_client/orchestrator_v2.py` | `_consume_sc_killed_pid` | 215-235 | function | Return True (and clear the entry) if `pid` was recently stamped as SC-killed. |
| `chatroom_client/orchestrator_v2.py` | `_prompt_prefix_for_room` | 267-270 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_agent_session_state_slug` | 273-276 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_prompt_token_estimate` | 279-280 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_prompt_audit_sections` | 283-304 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_normalize_service_tier` | 307-309 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_effective_service_tier` | 312-316 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_server_wake_category` | 319-321 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_load_persisted_agent_config` | 324-348 | function | Read persisted dropdown selection (model + effort) from server_state.json. |
| `chatroom_client/orchestrator_v2.py` | `_detect_media_type` | 351-360 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_resize_image_if_needed` | 363-404 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_resolve_attachment_url` | 407-413 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_is_loopback_host` | 416-417 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_append_unique_url` | 420-422 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_configured_attachment_https_bases` | 425-441 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_url_for_base` | 444-462 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_is_model_fetchable_image_url` | 465-467 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_model_url` | 470-483 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_fetch_candidates` | 486-504 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_fetch_attachment_bytes` | 507-514 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_filename` | 517-518 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_media_type` | 521-522 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_is_image_attachment` | 525-532 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_extract_attachment_text` | 535-562 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_id_from_att` | 565-575 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_load_transfers_manifest` | 578-593 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_display_attachment_disk_path` | 596-600 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_transfer_dirs` | 603-613 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_attachment_disk_path` | 616-631 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `_format_attachment_text_block` | 634-651 | function | Function block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator` | 654-4714 | class | Per-agent orchestrator for one long-lived `claude -p` session. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.__init__` | 708-910 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._session_state_path` | 912-917 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._fresh_restart_flag_path` | 919-920 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restart_marker_path` | 922-923 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restart_marker_spawn_seen_path` | 925-932 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_restart_marker_spawn_seen` | 934-953 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restart_marker_spawn_reason` | 955-985 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._harness_for_model_name` | 987-989 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._is_resume_capable_harness` | 991-992 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._fresh_restart_spawn_reason` | 994-1008 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._load_persisted_session_state` | 1010-1087 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._persist_session_state` | 1089-1110 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._clear_persisted_session_state` | 1112-1119 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._prefer_resume_mode` | 1121-1122 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._clear_in_memory_session_state` | 1124-1128 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claude_transcript_candidates` | 1130-1142 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._validate_claude_resume_session` | 1144-1163 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._normalize_connect_event` | 1166-1170 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restart_event_from_reason` | 1172-1176 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._activity_lifecycle_for_connect_event` | 1178-1201 | method | Map the current respawn cause to an Activity lifecycle (event, verb). |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._ensure_runtime_tasks` | 1203-1223 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._runtime_task_done` | 1225-1256 | method | Done-callback for supervised runtime loops. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._reschedule_runtime_tasks_if_running` | 1258-1264 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restore_from_auth_dormant` | 1266-1276 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.start` | 1278-1298 | async method | Start the per-agent runtime. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.stop` | 1300-1319 | async method | Stop the per-agent runtime. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.inject_message` | 1321-1322 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_wake_event` | 1324-1344 | async method | Accept a server-authored wake_event frame and queue a runtime wake. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._build_server_wake_message` | 1346-1553 | async method | Build a pending wake from a server-authored wake_event payload. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_event_messages` | 1556-1577 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._silent_marker_message_ids` | 1580-1599 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._silent_marker_message_ids_for_server_wake` | 1602-1612 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._compose_mode_suffix` | 1614-1615 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._apply_mode_layers` | 1617-1630 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._sync_mode_layers` | 1632-1649 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.set_mode_suffix` | 1651-1652 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.set_host_mode` | 1654-1656 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.set_collab_mode` | 1658-1687 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.clear_collab_mode` | 1689-1697 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.switch_effort` | 1699-1708 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._hot_switch_codex_effort` | 1710-1729 | async method | Apply an effort change to the live Codex app-server wrapper without a respawn. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.switch_service_tier` | 1731-1737 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.switch_model` | 1739-1755 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_session_info` | 1757-1860 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_participant_updated` | 1862-1874 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_reaction_update` | 1876-1921 | async method | Handle reactions. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._reaction_targets_self` | 1923-1936 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_buffer_held` | 1938-1952 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_buffer_released` | 1954-1971 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.handle_buffer_revise_opportunity` | 1973-2017 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._queue_claim_continuation` | 2020-2081 | async method | Owner-only follow-up wake fired after a [CLAIM:] is registered + broadcast. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._open_claim` | 2083-2093 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._git_status_porcelain` | 2095-2109 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_noop_close_cleanliness` | 2111-2129 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._mark_claim_activity` | 2131-2140 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._cancel_turn_working_guard` | 2143-2148 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._note_real_activity` | 2150-2155 | method | Mark that real model/tool/text output has started for this turn. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._start_turn_working_guard` | 2157-2184 | async method | Start the harness-neutral guard: after delay, post 'working' activity row + heartbeats with coarse phase until real activity arrives or turn ends. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._close_claim` | 2186-2236 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._extract_claim_label` | 2239-2241 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._reconcile_blocked_local_claim` | 2243-2276 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_flag_path` | 2278-2280 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._write_claim_flag` | 2282-2288 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._clear_claim_flag` | 2290-2296 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._enqueue_self_review_wake` | 2298-2323 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._workspace_doc_path` | 2325-2329 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._workspace_doc_review_watermark_path` | 2331-2342 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._workspace_doc_enabled_value` | 2344-2361 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._workspace_doc_enabled` | 2363-2364 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.workspace_doc_context_block` | 2366-2378 | method | Return the room workspace doc as prompt context when explicitly enabled. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claims_source_db_path` | 2380-2386 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_label_from_metadata` | 2389-2399 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_record_id` | 2402-2404 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._cross_workspace_claim_records` | 2406-2467 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._read_doc_review_watermark` | 2469-2477 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._write_doc_review_watermark` | 2479-2490 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.workspace_doc_review_startup_prompt` | 2492-2496 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._advance_workspace_doc_review_watermark_if_pending` | 2498-2518 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.workspace_doc_startup_prompt` | 2520-2536 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._scan_workspace_doc_health` | 2539-2567 | method | Mechanical clobber seatbelt for a worker-edited WORKSPACE_DOC.md. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._enqueue_workspace_doc_check_wake` | 2569-2641 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._scan_doc_check_result` | 2643-2679 | async method | Run the clobber seatbelt after the worker closes its DOC CHECK turn. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._run_claims_log_generator` | 2681-2690 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claims_log_refresh_paths` | 2692-2694 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._mark_claims_log_refresh_pending` | 2696-2704 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._clear_claims_log_refresh_pending` | 2706-2711 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._write_claims_log_refresh_lock_marker` | 2713-2720 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._acquire_claims_log_refresh_lock` | 2722-2738 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._drain_claims_log_refresh_pending` | 2740-2761 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._refresh_claims_logs_after_self_review` | 2763-2798 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._queue_claims_log_refresh_after_self_review` | 2800-2814 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._api_release_claim` | 2816-2826 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._api_refresh_claim` | 2828-2841 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_is_terminal_text` | 2843-2861 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_watchdog_loop` | 2863-2866 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_watchdog_tick` | 2868-2904 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._spawn` | 2908-3166 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._current_harness_label` | 3168-3175 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._cleanup_stale_prompt_files` | 3177-3187 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._kill_stale_claude_processes` | 3189-3224 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._kill` | 3226-3282 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._restart` | 3284-3330 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._enter_crash_cooldown` | 3332-3365 | async method | Failure/hang guard tripped. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._schedule_auto_resume` | 3367-3372 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._auto_resume_after_cooldown` | 3374-3382 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._send_local_alert` | 3384-3391 | async method | Windows toast for orchestrator-level alerts (crash loop, watchdog cap). |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._watchdog_recycle_reason` | 3393-3432 | method | Decide whether an open turn is wedged and should be recycled. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._watchdog` | 3434-3459 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._process_is_busy` | 3461-3496 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._recover_failed_fast_spawn` | 3498-3528 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._stdout_reader` | 3530-3571 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._handle_stdout_entry` | 3573-3936 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._rescue_pending_plan_text` | 3938-3948 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._stderr_reader` | 3950-3991 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_meta` | 3994-4021 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_kind` | 4024-4026 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_reason` | 4029-4031 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_interruptible` | 4034-4036 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._claim_owner_progress_should_emit` | 4038-4057 | method | True when stale ambient suppression must NOT muzzle this turn's text. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_room_version` | 4060-4065 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._wake_cursor_after_id` | 4068-4070 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._refresh_wake_missed_block` | 4072-4073 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._note_room_activity` | 4075-4076 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._latest_included_message_id` | 4079-4080 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._queue_depth` | 4082-4083 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._write_interrupt_flag` | 4085-4086 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._reset_active_turn_state` | 4088-4089 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._clear_wake_buffers` | 4091-4092 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._begin_active_turn` | 4094-4095 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._enqueue_wake` | 4097-4098 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._next_queued_wake` | 4100-4101 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._message_consumer` | 4103-4104 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._enter_auth_dormant` | 4106-4120 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._auth_probe_loop` | 4122-4152 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator.send_metadata` | 4154-4160 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._append_attachment_text_context` | 4162-4201 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._write_prompt_assembly_audit` | 4203-4253 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._send_to_claude` | 4255-4314 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._snapshot_workspace_generated_media` | 4316-4322 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._emit_new_workspace_generated_media` | 4324-4339 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._fetch_startup_messages` | 4341-4373 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._fetch_missed_messages` | 4375-4376 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._inject_startup_context` | 4378-4504 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._inject_compaction_recovery` | 4506-4551 | async method | After compaction, re-inject identity/authority/workspace-doc context only. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._begin_plan_approval` | 4553-4569 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._resolve_plan_approval` | 4571-4598 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._maybe_handle_plan_approval_message` | 4600-4601 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._reaction_contains` | 4604-4606 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._format_reaction_summary` | 4608-4618 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._read_latest_plan_file` | 4621-4631 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._send_status` | 4633-4634 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._send_doc_status` | 4636-4637 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._emit_debug` | 4639-4687 | async method | Async method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._notify_monitor` | 4689-4696 | method | Method block. |
| `chatroom_client/orchestrator_v2.py` | `ChatroomOrchestrator._load_state` | 4698-4714 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `_parse_plan_approval_text` | 31-53 | function | Parse Marc's plan decision from a text reply, preserving approve notes. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter` | 56-981 | class | Own wake injection, pending-wake queueing, and turn-state transitions. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter.__init__` | 59-60 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._latest_included_message_id` | 63-69 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._receipt_ids_for` | 71-72 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._merge_receipt_ids` | 74-78 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._post_ai_seen_receipts` | 80-112 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._flush_active_turn_ai_seen_receipts` | 114-125 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._emit_ai_seen_receipts_for_wake` | 127-153 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._counts_for_hot_cadence` | 156-160 | method | True for real room participant chat that should advance HOT cadence. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter.inject_message` | 162-518 | async method | Turn a room message into a per-agent wake prompt when needed. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._refresh_wake_missed_block` | 520-598 | async method | Merge messages newer than the wake's baked cursor into the prompt. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._note_room_activity` | 600-603 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._write_interrupt_flag` | 605-633 | async method | Write a soft-interrupt flag readable by the PreToolUse hook. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._reset_active_turn_state` | 635-659 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._clear_wake_buffers` | 661-663 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._begin_active_turn` | 665-687 | method | Method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._enqueue_wake` | 689-812 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._next_queued_wake` | 814-842 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._message_consumer` | 844-937 | async method | Async method block. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._fetch_missed_messages` | 939-967 | async method | Return all room messages after our subprocess's last-seen cursor. |
| `chatroom_client/orchestrator_wakes.py` | `WakeRouter._maybe_handle_plan_approval_message` | 969-981 | method | Method block. |
| `chatroom_client/platform.py` | `_create_job_object` | 17-75 | function | Create a Job Object that kills all children when parent exits. |
| `chatroom_client/platform.py` | `_ensure_single_instance` | 81-104 | function | Exit if another instance is already running. |
| `chatroom_client/platform.py` | `_claude_bin_from_env` | 115-127 | function | Claude binary recorded by first-run (CLAUDE_BIN_PATH), or "". |
| `chatroom_client/platform.py` | `hidden_subprocess_kwargs` | 130-142 | function | Return subprocess kwargs that fully suppress console windows on Windows. |
| `chatroom_client/platform.py` | `find_claude_command` | 145-189 | function | Return the full command prefix to invoke claude -p without a visible console. |
| `chatroom_client/restart_log.py` | `_normalize_room` | 33-35 | function | Function block. |
| `chatroom_client/restart_log.py` | `_test_telemetry_disabled` | 38-42 | function | Function block. |
| `chatroom_client/restart_log.py` | `log_spawn` | 45-72 | function | Append a spawn event. |
| `chatroom_client/restart_log.py` | `_trim_if_oversized` | 75-90 | function | Keep file bounded. |
| `chatroom_client/restart_log.py` | `_read_entries` | 93-113 | function | Function block. |
| `chatroom_client/restart_log.py` | `summarize_recent_spawns` | 116-165 | function | Return a compact per-room summary, or empty string if nothing noteworthy. |
| `chatroom_client/restart_log.py` | `log_compaction` | 171-197 | function | Append a context-window compaction event. |
| `chatroom_client/restart_log.py` | `summarize_recent_compactions` | 200-252 | function | Return a one-line compaction summary for the current room window, or empty string. |
| `chatroom_client/roomevent.py` | `context_lane_policy` | 64-67 | function | Return the gate policy for a context lane. |
| `chatroom_client/roomevent.py` | `RoomEvent` | 75-101 | class | Policy-enriched representation of a chatroom event. |
| `chatroom_client/roomevent.py` | `ProjectionSkip` | 105-107 | class | Class block. |
| `chatroom_client/roomevent.py` | `ProjectionResult` | 111-115 | class | Class block. |
| `chatroom_client/roomevent.py` | `_apply_policy` | 122-320 | function | Return the policy field dict for a given (msg_type, subtype). |
| `chatroom_client/roomevent.py` | `_subtype_from_dict` | 367-373 | function | Function block. |
| `chatroom_client/roomevent.py` | `room_event_from_dict` | 376-402 | function | Adapt a raw chatroom_messages row (dict) to a RoomEvent. |
| `chatroom_client/roomevent.py` | `room_event_from_chat_message` | 405-438 | function | Adapt a ChatMessage object or raw dict to a RoomEvent. |
| `chatroom_client/roomevent.py` | `_is_visible` | 445-458 | function | Return (visible: bool, skip_reason: str). |
| `chatroom_client/roomevent.py` | `project_room_events` | 461-499 | function | Project a sequence of events through the policy layer for one audience/purpose. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator` | 47-448 | class | Manages one-shot highest-tier model_runner turns for thinker sessions. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.__init__` | 50-78 | method | Method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._resolve_prompt_path` | 80-87 | method | Method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.start` | 90-96 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.stop` | 98-103 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.handle_session_turn` | 106-112 | async method | Signaled by the coordinator after the other Thinker posts a turn. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.handle_session_respond` | 114-119 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._poll_loop` | 121-129 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._run_turn` | 131-150 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._spawn_and_collect` | 153-252 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._read_system_prompt` | 254-262 | method | Method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._kill_current` | 264-283 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._fetch_active_session` | 286-293 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._fetch_session` | 295-300 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._post_contribution` | 302-312 | async method | Async method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator.send_signal` | 314-325 | async method | POST a coordination signal to the thinker session coordinator. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._build_prompt` | 328-332 | method | Method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._build_synthesis_prompt` | 334-376 | method | Method block. |
| `chatroom_client/thinker.py` | `ThinkerOrchestrator._build_freeform_prompt` | 378-448 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager` | 28-128 | class | System tray icon showing connection status and child process counts. |
| `chatroom_client/tray.py` | `TrayManager.__init__` | 36-47 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager._make_icon_image` | 49-59 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager._build_tooltip` | 61-65 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager._build_menu` | 67-71 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager._handle_restart` | 73-75 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager._handle_quit` | 77-79 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager.set_callbacks` | 81-83 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager.set_status` | 85-90 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager.set_child_counts` | 92-102 | method | Compatibility shim for orchestrator callsites — no longer rendered. |
| `chatroom_client/tray.py` | `TrayManager.start` | 104-123 | method | Method block. |
| `chatroom_client/tray.py` | `TrayManager.stop` | 125-128 | method | Method block. |
| `chatroom_client/turn_pipeline.py` | `normalize_token_line` | 77-79 | function | Canonicalize a line for token matching: strip, drop trailing .!?, upper. |
| `chatroom_client/turn_pipeline.py` | `split_leading_filler_token` | 82-97 | function | If the first non-blank line is a filler token, return (token, rest). |
| `chatroom_client/turn_pipeline.py` | `strip_trailing_filler_lines` | 100-116 | function | Remove trailing lines that are only filler tokens. |
| `chatroom_client/turn_pipeline.py` | `strip_drk_line_leaks` | 119-142 | function | Strip whole-line DRK verbs anywhere in the text. |
| `chatroom_client/turn_pipeline.py` | `is_bare_drk_verb` | 145-150 | function | True if the entire text is a single canonicalized control token. |
| `chatroom_client/turn_pipeline.py` | `strip_md_wrappers` | 158-160 | function | Strip leading/trailing markdown delimiters before sentinel comparisons. |
| `chatroom_client/turn_pipeline.py` | `strip_hallucinated_turns` | 163-174 | function | Strip lines that look like chatroom room-tail format ([HH:MM:SS] - Agent:). |
| `chatroom_client/turn_pipeline.py` | `normalize_outbound_text` | 177-193 | function | Apply the standard outbound normalization: drop [rerun:bN], strip leading/trailing filler tokens, collapse 'Silent' sentinel to empty. |
| `chatroom_client/turn_pipeline.py` | `is_filler` | 198-222 | function | Detect room-noise / meta-narration that shouldn't ship to chat. |
| `chatroom_client/turn_pipeline.py` | `is_image_complaint` | 225-230 | function | Function block. |
| `chatroom_client/turn_pipeline.py` | `hash_text` | 235-236 | function | Function block. |
| `chatroom_client/turn_pipeline.py` | `is_duplicate_visible_send` | 239-257 | function | True if `text` matches the last-emitted hash within the window AND was emitted within the same wake/turn (event key). |
| `chatroom_client/turn_pipeline.py` | `structural_signature` | 265-280 | function | Return a normalized signature of a message's opening phrasing. |
| `chatroom_client/turn_pipeline.py` | `is_structural_duplicate` | 283-299 | function | True if `text`'s opener signature matches any in `recent_signatures`. |
| `chatroom_client/turn_pipeline.py` | `scan_output_tokens` | 304-338 | function | Scan all output lines for buffer-decision action tokens. |
| `chatroom_client/turn_pipeline.py` | `parse_buffer_decision` | 341-362 | function | Parse fresh-decision CC output into a dict suitable for POSTing. |
| `chatroom_client/workspace_hot_overview.py` | `_env_int` | 19-23 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_read_json` | 32-37 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_hot_items` | 40-45 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_has_memory_items` | 48-49 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_entry_id` | 52-59 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_hash_text` | 62-63 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_memory_file_content` | 66-72 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_snapshot_tail` | 75-86 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_workspace_roots` | 89-96 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `_workspace_meta` | 99-105 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `workspace_hot_entries` | 108-134 | function | Return current Short_Memory bullet entries from all non-archived workspaces. |
| `chatroom_client/workspace_hot_overview.py` | `_format_workspace_memory_section` | 137-159 | function | Function block. |
| `chatroom_client/workspace_hot_overview.py` | `build_workspace_hot_overview` | 162-215 | function | Regenerate Main's legacy spawn snapshot from non-archived workspace SHORT files. |
| `chatroom_client/workspace_hot_overview.py` | `format_workspace_hot_delta` | 218-239 | function | Format a Short_Memory delta batch for Main live updates. |
| `chatroom_client/workspace_hot_overview.py` | `write_workspace_hot_delta_prompt` | 242-253 | function | Write the human/debug-visible delta prompt file. |
| `chatroom_client/workspace_hot_overview.py` | `append_workspace_hot_delta_delivery` | 256-268 | function | Append one proof-of-delivery row for a Main workspace SHORT delta flush. |
| `chatroom_prompts.py` | `_prompt_path` | 55-61 | function | Function block. |
| `chatroom_prompts.py` | `_load_sections` | 64-73 | function | Function block. |
| `chatroom_prompts.py` | `get_prompt_section` | 76-82 | function | Function block. |
| `chatroom_prompts.py` | `protect_template_literals` | 85-87 | function | Keep authored {{TOKEN}} text inert while a prompt shell renders. |
| `chatroom_prompts.py` | `restore_template_literals` | 90-91 | function | Function block. |
| `chatroom_prompts.py` | `_safe_replacement` | 94-95 | function | Function block. |
| `chatroom_prompts.py` | `render_prompt_section` | 98-114 | function | Function block. |
| `chatroom_prompts.py` | `load_prompt_text` | 117-128 | function | Read a prompt file verbatim (no SECTION parsing) and apply {{KEY}} replacements. |
| `chatroom_prompts.py` | `build_sealed_sections` | 131-148 | function | Build the {filename: {section: text}} map for the embedded-constants module, parsing the must-protect SECTION prompts from ``prompts_root`` (the staged payload tree at build time). |
| `chatroom_prompts.py` | `get_collab_mode_catalog` | 151-157 | function | Function block. |
| `config/identity.py` | `identity_config` | 15-21 | function | Function block. |
| `config/identity.py` | `_user_block` | 24-26 | function | Function block. |
| `config/identity.py` | `_collab_block` | 29-31 | function | Function block. |
| `config/identity.py` | `_governance_block` | 34-36 | function | Function block. |
| `config/identity.py` | `_agents_block` | 39-41 | function | Function block. |
| `config/identity.py` | `_agent_block` | 44-46 | function | Function block. |
| `config/identity.py` | `_string_list` | 49-52 | function | Function block. |
| `config/identity.py` | `_derived_user_tokens` | 55-69 | function | Function block. |
| `config/identity.py` | `user_display_name` | 72-73 | function | Function block. |
| `config/identity.py` | `user_id` | 76-77 | function | Function block. |
| `config/identity.py` | `user_full_name` | 80-82 | function | Function block. |
| `config/identity.py` | `user_legacy_sender_ids` | 85-87 | function | Function block. |
| `config/identity.py` | `user_mention_aliases` | 90-97 | function | Function block. |
| `config/identity.py` | `user_sender_ids` | 100-101 | function | Function block. |
| `config/identity.py` | `user_code_author_id` | 104-106 | function | Function block. |
| `config/identity.py` | `user_name_lower` | 109-110 | function | Function block. |
| `config/identity.py` | `user_wake_label` | 113-114 | function | Function block. |
| `config/identity.py` | `user_person_entity_id` | 117-118 | function | Function block. |
| `config/identity.py` | `user_name_exclusion_tokens` | 121-127 | function | Function block. |
| `config/identity.py` | `governance_owner_id` | 130-140 | function | Function block. |
| `config/identity.py` | `governance_curator_id` | 143-146 | function | Function block. |
| `config/identity.py` | `collab_host_display_name` | 149-150 | function | Function block. |
| `config/identity.py` | `collab_host_notes_label` | 153-157 | function | Function block. |
| `config/identity.py` | `is_user_sender` | 160-161 | function | Function block. |
| `config/identity.py` | `agent_participant_id` | 164-169 | function | Function block. |
| `config/identity.py` | `agent_display_name` | 172-177 | function | Function block. |
| `config/identity.py` | `participant_display_name` | 180-190 | function | Function block. |
| `config/identity.py` | `participant_name_map` | 193-205 | function | Function block. |
| `config/identity.py` | `ingest_activity_display_names` | 208-218 | function | Function block. |
| `config/paths.py` | `program_root` | 30-35 | function | The installed code tree. |
| `config/paths.py` | `load_env_file` | 38-65 | function | Load <program root>/.env into os.environ for keys not already set. |
| `config/paths.py` | `data_root` | 68-73 | function | Root for all mutable runtime data. |
| `config/paths.py` | `logs_dir` | 76-80 | function | Log directory under the data root. |
| `config/process_inventory.py` | `ScProcess` | 113-132 | class | A classified process. |
| `config/process_inventory.py` | `ScProcess.is_anomaly` | 131-132 | method | Method block. |
| `config/process_inventory.py` | `_first_token` | 135-137 | function | Function block. |
| `config/process_inventory.py` | `interpreter_kind` | 140-159 | function | Classify the interpreter as the real interpreter, the Store relauncher alias, or something else. |
| `config/process_inventory.py` | `_model_harness` | 162-177 | function | Function block. |
| `config/process_inventory.py` | `_participant_from_model_cmdline` | 180-187 | function | Function block. |
| `config/process_inventory.py` | `identify_participant` | 190-208 | function | Canonical participant identity, env-FIRST. |
| `config/process_inventory.py` | `_room_from_cmdline` | 211-235 | function | Best-effort room fallback for legacy/unenv-readable processes. |
| `config/process_inventory.py` | `room_of` | 238-241 | function | Room from ``SC_WORKSPACE_ID`` first, then stable cmdline markers. |
| `config/process_inventory.py` | `_supervisor_script` | 244-248 | function | Function block. |
| `config/process_inventory.py` | `_is_chatroom_client` | 251-252 | function | Function block. |
| `config/process_inventory.py` | `_chatroom_client_participant` | 255-261 | function | Function block. |
| `config/process_inventory.py` | `classify` | 264-350 | function | Classify a process snapshot. |
| `config/process_inventory.py` | `_is_wrapper_of` | 353-368 | function | True if `parent` is a NORMAL thin launcher whose real process is `child`: an identical-cmdline relaunch (e.g. |
| `config/process_inventory.py` | `_flag_wrappers` | 371-388 | function | Fold normal thin launchers (uvicorn master, cmd.exe->claude shell). |
| `config/process_inventory.py` | `_flag_duplicates` | 391-404 | function | A genuine duplicate = >1 REAL-interpreter agent supervisor for the same (participant, room). |
| `config/process_inventory.py` | `_flag_orphans` | 407-426 | function | An SC model child whose participant has no live real (or duplicate) supervisor is an orphan -- a child still running after its parent is gone. |
| `config/process_inventory.py` | `anomalies` | 429-431 | function | The subset a reconciler/health check should alarm on. |
| `config/process_inventory.py` | `curator_spawn_blocked` | 434-455 | function | Reason string when a Curator supervisor is alive but its model child is DOWN due to a recorded spawn failure; ``None`` when healthy or merely idle. |
| `config/repo_git.py` | `_hidden_subprocess_kwargs` | 10-17 | function | Function block. |
| `config/repo_git.py` | `_run_git` | 20-29 | function | Function block. |
| `config/repo_git.py` | `_git_stdout` | 32-36 | function | Function block. |
| `config/repo_git.py` | `git_status_for_path` | 39-103 | function | Function block. |
| `config/repos.py` | `_registry_path` | 32-33 | function | Function block. |
| `config/repos.py` | `_seed_default` | 36-44 | function | Function block. |
| `config/repos.py` | `_read_raw` | 47-61 | function | Function block. |
| `config/repos.py` | `_write_raw` | 64-67 | function | Function block. |
| `config/repos.py` | `list_repos` | 70-72 | function | Function block. |
| `config/repos.py` | `get_repo` | 75-82 | function | Function block. |
| `config/repos.py` | `default_slug` | 85-90 | function | Function block. |
| `config/repos.py` | `resolve_root` | 93-102 | function | Return the absolute root path for a repo slug (default repo when None/empty). |
| `config/repos.py` | `_validate_slug` | 105-109 | function | Function block. |
| `config/repos.py` | `_validate_path` | 112-118 | function | Function block. |
| `config/repos.py` | `add_repo` | 121-132 | function | Function block. |
| `config/repos.py` | `remove_repo` | 135-146 | function | Function block. |
| `config/repos.py` | `update_repo` | 149-163 | function | Function block. |
| `config/service_urls.py` | `_first_env` | 19-24 | function | Function block. |
| `config/service_urls.py` | `public_http_base` | 27-29 | function | Browser/agent-facing HTTPS API base URL. |
| `config/service_urls.py` | `public_ws_base` | 32-42 | function | Browser/agent-facing WebSocket base URL without a path. |
| `config/service_urls.py` | `local_http_base` | 45-50 | function | Local process-to-API HTTP base URL. |
| `config/service_urls.py` | `pms_v2_http_base` | 53-58 | function | PMS v2 API base URL. |
| `config/service_urls.py` | `ollama_http_base` | 61-63 | function | Retired local embedding API base URL. |
| `config/service_urls.py` | `activity_event_url` | 66-67 | function | Function block. |
| `config/service_urls.py` | `chatroom_history_url` | 70-71 | function | Function block. |
| `config/settings.py` | `Settings` | 12-249 | class | Application configuration. |
| `config/settings.py` | `get_settings` | 251-253 | function | Return a cached Settings instance. |
| `config/thinker_prompts.py` | `render_thinker_prompt_section` | 12-16 | function | Function block. |
| `firstrun/bootstrap.py` | `PhaseResult` | 108-116 | class | Class block. |
| `firstrun/bootstrap.py` | `PhaseResult.line` | 113-116 | method | Method block. |
| `firstrun/bootstrap.py` | `phase_dirs` | 121-138 | function | Function block. |
| `firstrun/bootstrap.py` | `_is_placeholder` | 143-144 | function | Function block. |
| `firstrun/bootstrap.py` | `phase_env` | 147-196 | function | Function block. |
| `firstrun/bootstrap.py` | `_key_value` | 199-204 | function | Function block. |
| `firstrun/bootstrap.py` | `phase_certs` | 209-261 | function | Function block. |
| `firstrun/bootstrap.py` | `phase_db` | 266-306 | function | Function block. |
| `firstrun/bootstrap.py` | `_tls_context` | 311-330 | function | HTTPS context that trusts a baked-in CA bundle, not the OS trust state. |
| `firstrun/bootstrap.py` | `_ensure_private_node` | 333-359 | function | Download/extract SC's private portable Node. |
| `firstrun/bootstrap.py` | `_ensure_pwsh` | 362-386 | function | Download/extract SC's private PowerShell 7. |
| `firstrun/bootstrap.py` | `_add_dir_to_user_path` | 389-412 | function | Prepend a directory to the HKCU PATH so future SC launches inherit it. |
| `firstrun/bootstrap.py` | `_install_grok_cli` | 415-450 | function | Install the xAI Grok CLI via the official x.ai script; persist GROK_BIN_PATH. |
| `firstrun/bootstrap.py` | `_ensure_anthropic_shell` | 453-460 | function | Provision PowerShell 7 + wire it onto PATH for the Anthropic provider. |
| `firstrun/bootstrap.py` | `_npm_install_cli` | 463-482 | function | Install an npm CLI into SC's private prefix using the private node. |
| `firstrun/bootstrap.py` | `_upsert_env_line` | 485-493 | function | Function block. |
| `firstrun/bootstrap.py` | `phase_clis` | 496-571 | function | Auto-install the selected provider's CLI when it is missing. |
| `firstrun/bootstrap.py` | `_deploy_vc_runtime` | 577-605 | function | App-local VC++ runtime next to every native binary that needs it. |
| `firstrun/bootstrap.py` | `_pick_cli_entrypoint` | 608-625 | function | Prefer the vendored native .exe over the npm shim chain. |
| `firstrun/bootstrap.py` | `_verify_cli_answers` | 628-640 | function | 'npm exited 0' is not 'the CLI works' — require real output. |
| `firstrun/bootstrap.py` | `phase_tasks` | 645-669 | function | Function block. |
| `firstrun/bootstrap.py` | `_find_cli` | 674-693 | function | Locate the provider CLI. |
| `firstrun/bootstrap.py` | `_cli_display` | 696-697 | function | Function block. |
| `firstrun/bootstrap.py` | `phase_backend` | 700-718 | function | Function block. |
| `firstrun/bootstrap.py` | `_exec_argv` | 735-740 | function | Make an argv actually executable: .cmd/.bat shims must be launched through cmd.exe (CreateProcess rejects them with WinError 193). |
| `firstrun/bootstrap.py` | `_cli_signed_in` | 743-765 | function | Live auth probe where the CLI supports one; file heuristic otherwise. |
| `firstrun/bootstrap.py` | `_run_login_streaming` | 771-806 | function | Run `<cli> login`, echoing output and opening the auth URL ourselves. |
| `firstrun/bootstrap.py` | `_run_login_new_console` | 809-825 | function | Last resort: pop a fresh console window already running the login, then poll auth status here until it lands (or the user gives up). |
| `firstrun/bootstrap.py` | `_offer_sign_in` | 828-854 | function | Interactive sign-in: we run the login and open the browser ourselves. |
| `firstrun/bootstrap.py` | `_next_steps_text` | 857-880 | function | Function block. |
| `firstrun/bootstrap.py` | `main` | 896-980 | function | Function block. |
| `integrity/core_seal.py` | `IntegrityResult` | 81-107 | class | Class block. |
| `integrity/core_seal.py` | `IntegrityResult.is_clean` | 90-91 | method | Method block. |
| `integrity/core_seal.py` | `IntegrityResult.summary` | 93-107 | method | Method block. |
| `integrity/core_seal.py` | `_posix` | 110-111 | function | Function block. |
| `integrity/core_seal.py` | `_is_leeway` | 114-115 | function | Function block. |
| `integrity/core_seal.py` | `sealed_relpaths` | 118-144 | function | Sorted POSIX relpaths of every sealed file under ``root``. |
| `integrity/core_seal.py` | `_sha256_file` | 147-152 | function | Function block. |
| `integrity/core_seal.py` | `build_manifest` | 155-159 | function | Build the unsigned manifest dict for the tree at ``root``. |
| `integrity/core_seal.py` | `_canonical_payload` | 162-165 | function | Stable bytes of the manifest body (signature excluded) for signing. |
| `integrity/core_seal.py` | `_load_signing_key` | 168-183 | function | Ed25519 private key from SC_SEAL_KEY (PEM path), or None. |
| `integrity/core_seal.py` | `_embedded_public_key` | 186-200 | function | The committed Ed25519 public key used to verify the manifest, or None. |
| `integrity/core_seal.py` | `write_manifest` | 203-220 | function | Generate and write ``core_manifest.json`` into ``root``. |
| `integrity/core_seal.py` | `verify` | 223-278 | function | Verify the program tree at ``root`` (default: program_root()). |
| `memory/ai/profile_manager.py` | `AIProfileManager` | 26-243 | class | Manages AI model family profiles with domain scoring and accuracy tracking. |
| `memory/ai/profile_manager.py` | `AIProfileManager.__init__` | 29-31 | method | Method block. |
| `memory/ai/profile_manager.py` | `AIProfileManager.ensure_profile` | 33-62 | async method | Get or create a profile for a model family. |
| `memory/ai/profile_manager.py` | `AIProfileManager.get_profile` | 64-73 | async method | Get a profile by model family name. |
| `memory/ai/profile_manager.py` | `AIProfileManager.list_profiles` | 75-81 | async method | List all AI profiles. |
| `memory/ai/profile_manager.py` | `AIProfileManager.record_claim` | 83-99 | async method | Record that a model family made a new claim. |
| `memory/ai/profile_manager.py` | `AIProfileManager.record_validation` | 101-110 | async method | Record that a claim from this family was validated. |
| `memory/ai/profile_manager.py` | `AIProfileManager.record_contradiction` | 112-121 | async method | Record that a claim from this family was contradicted. |
| `memory/ai/profile_manager.py` | `AIProfileManager.record_cross_family_agreement` | 123-138 | async method | Record that two different families agreed on something. |
| `memory/ai/profile_manager.py` | `AIProfileManager.record_cross_family_disagreement` | 140-155 | async method | Record that two different families disagreed. |
| `memory/ai/profile_manager.py` | `AIProfileManager.update_domain_score` | 157-172 | async method | Adjust a domain expertise score. |
| `memory/ai/profile_manager.py` | `AIProfileManager.refresh_stats_from_db` | 174-176 | async method | No-op: ai_reasoning table removed. |
| `memory/ai/profile_manager.py` | `AIProfileManager.get_family_comparison` | 178-196 | async method | Compare all model families side by side. |
| `memory/ai/profile_manager.py` | `AIProfileManager._insert_profile` | 200-222 | async method | Insert a new profile into the database. |
| `memory/ai/profile_manager.py` | `AIProfileManager._row_to_profile` | 224-243 | method | Convert a database row to an AIProfile instance. |
| `memory/api/activity_routes.py` | `_env_int` | 49-53 | function | Function block. |
| `memory/api/activity_routes.py` | `_is_curator_debug_only_event` | 124-129 | function | Function block. |
| `memory/api/activity_routes.py` | `ActivityEvent` | 134-146 | class | Class block. |
| `memory/api/activity_routes.py` | `_is_retired_agent` | 149-151 | function | Function block. |
| `memory/api/activity_routes.py` | `_should_replay_event` | 154-165 | function | Function block. |
| `memory/api/activity_routes.py` | `_track_active_tool_state` | 173-197 | function | Function block. |
| `memory/api/activity_routes.py` | `_open_tool_age_s` | 200-209 | function | Function block. |
| `memory/api/activity_routes.py` | `open_tools_snapshot` | 212-242 | function | Open tool blocks for one room, pruning entries older than the TTL. |
| `memory/api/activity_routes.py` | `active_tool_agents` | 245-262 | function | Return agents that currently have a tool block open in the given room. |
| `memory/api/activity_routes.py` | `_read_activity_log_tail_lines` | 265-278 | function | Function block. |
| `memory/api/activity_routes.py` | `_read_persisted_events` | 281-298 | function | Function block. |
| `memory/api/activity_routes.py` | `_persist_event` | 301-313 | function | Function block. |
| `memory/api/activity_routes.py` | `_normalize_room_id` | 316-318 | function | Function block. |
| `memory/api/activity_routes.py` | `_ensure_event_room` | 321-329 | function | Function block. |
| `memory/api/activity_routes.py` | `_extract_claim_label` | 332-337 | function | Function block. |
| `memory/api/activity_routes.py` | `_is_claim_terminal_text` | 340-342 | function | Function block. |
| `memory/api/activity_routes.py` | `_parse_activity_ts` | 345-357 | function | Function block. |
| `memory/api/activity_routes.py` | `_within_terminal_grace` | 360-366 | function | Function block. |
| `memory/api/activity_routes.py` | `_is_missing_claim_label` | 369-370 | function | Function block. |
| `memory/api/activity_routes.py` | `_lookup_active_claim_label` | 373-438 | function | Function block. |
| `memory/api/activity_routes.py` | `_apply_file_diff_claim_fallback` | 441-467 | function | Function block. |
| `memory/api/activity_routes.py` | `_stamp_file_diff_claim` | 470-471 | function | Function block. |
| `memory/api/activity_routes.py` | `_ensure_file_diff_table` | 474-588 | function | Function block. |
| `memory/api/activity_routes.py` | `_ensure_activity_events_table` | 591-660 | function | Function block. |
| `memory/api/activity_routes.py` | `_ensure_activity_prune_trigger` | 663-702 | function | Function block. |
| `memory/api/activity_routes.py` | `_ensure_activity_events_schema_once` | 705-716 | function | Function block. |
| `memory/api/activity_routes.py` | `ensure_activity_events_schema` | 719-721 | function | Function block. |
| `memory/api/activity_routes.py` | `_persist_activity_event_db` | 724-751 | function | Function block. |
| `memory/api/activity_routes.py` | `_event_from_activity_row` | 754-778 | function | Function block. |
| `memory/api/activity_routes.py` | `_normalize_event_filters` | 781-789 | function | Function block. |
| `memory/api/activity_routes.py` | `_event_room_id` | 792-798 | function | Function block. |
| `memory/api/activity_routes.py` | `_read_activity_page` | 801-861 | function | Function block. |
| `memory/api/activity_routes.py` | `_event_dedupe_key` | 864-872 | function | Function block. |
| `memory/api/activity_routes.py` | `_merge_recent_activity` | 875-893 | function | Merge DB-backed events with the JSONL/ring replay buffer, newest first. |
| `memory/api/activity_routes.py` | `_persist_file_diff_event` | 896-982 | function | Function block. |
| `memory/api/activity_routes.py` | `publish_activity_data` | 985-1020 | async function | Publish an already-built activity event through the same live + durable path. |
| `memory/api/activity_routes.py` | `_bridge_lifecycle_to_debug` | 1034-1083 | async function | Mirror a debug/lifecycle event into the Debug stream -- live AND durable. |
| `memory/api/activity_routes.py` | `receive_activity_event` | 1089-1102 | async function | Receive an activity event from a subprocess runner. |
| `memory/api/activity_routes.py` | `recent_activity` | 1106-1133 | async function | Return a cursor page of activity events, newest first. |
| `memory/api/activity_routes.py` | `_normalize_completion_room_ids` | 1136-1146 | function | Function block. |
| `memory/api/activity_routes.py` | `_read_recent_completions` | 1149-1231 | function | Read the most recent [CLAIM COMPLETE:] posts across all rooms. |
| `memory/api/activity_routes.py` | `recent_completions` | 1235-1244 | async function | Recent [CLAIM COMPLETE:] posts across all rooms, newest first. |
| `memory/api/activity_routes.py` | `activity_open_tools` | 1248-1250 | async function | Current open tool blocks per agent in a room (TTL-pruned). |
| `memory/api/activity_routes.py` | `activity_stream` | 1254-1299 | async function | SSE endpoint streaming live activity events to connected viewers. |
| `memory/api/app.py` | `AppState` | 67-96 | class | Holds shared service instances for the application lifetime. |
| `memory/api/app.py` | `_dotenv_value` | 102-115 | function | Read one simple KEY=VALUE from the repo .env without loading secrets. |
| `memory/api/app.py` | `_runtime_env` | 118-125 | function | Function block. |
| `memory/api/app.py` | `_v2_primary_runtime_enabled` | 128-130 | function | Function block. |
| `memory/api/app.py` | `_pms_v2_runtime_db_path` | 133-136 | function | Function block. |
| `memory/api/app.py` | `_ensure_v2_thinker_schema` | 139-175 | async function | Create the v2-owned operational table used by Thinker sessions. |
| `memory/api/app.py` | `_ensure_v2_ideas_runtime_schema` | 178-205 | async function | Create v2-owned operational tables used by Thinker sessions. |
| `memory/api/app.py` | `_ensure_v2_curator_observations_schema` | 208-253 | async function | Create v2-owned curator_observations table -- the live source for Ideas tab and Thinker intake after the 2026-06-15 canonical tier removal. |
| `memory/api/app.py` | `_ensure_v2_thinker_intake_schema` | 256-305 | async function | Create the v2-owned thinker_intake table -- the fast-lane work queue from Concierge to Thinker. |
| `memory/api/app.py` | `_ensure_v2_collab_schema` | 308-533 | async function | Create the v2-owned operational tables used by Guest Mode. |
| `memory/api/app.py` | `_ensure_v2_task_queue_schema` | 536-582 | async function | Create the v2-owned operational table used by task queue approvals. |
| `memory/api/app.py` | `_ensure_v2_codespace_schema` | 585-622 | async function | Create the v2-owned tables backing the in-chatroom code editor. |
| `memory/api/app.py` | `_drop_retired_v2_tables` | 641-657 | async function | Idempotently drop retired-feature tables so they do not linger in a long-lived memory_v2.db. |
| `memory/api/app.py` | `lifespan` | 663-712 | async function | Application lifespan — initialize and tear down services. |
| `memory/api/app.py` | `_lifespan_startup_v2_primary` | 715-914 | async function | Start the API in PMS v2-primary mode without opening legacy memory.db. |
| `memory/api/app.py` | `_lifespan_startup` | 917-1322 | async function | All service initialization — extracted so lifespan can catch failures. |
| `memory/api/app.py` | `create_app` | 1327-1602 | function | Create and configure the FastAPI application. |
| `memory/api/asset_versioning.py` | `_content_hash` | 52-56 | function | Short, stable content hash of a file (sha256, hex-truncated). |
| `memory/api/asset_versioning.py` | `build_version_map` | 59-74 | function | Walk ``static_dir`` and hash every ``.js`` / ``.css`` asset. |
| `memory/api/asset_versioning.py` | `_asset_signature` | 77-90 | function | Cheap change detector for the hashed asset set. |
| `memory/api/asset_versioning.py` | `init_asset_versioning` | 93-99 | function | Build and cache the version map. |
| `memory/api/asset_versioning.py` | `get_version_map` | 102-110 | function | Return the current version map, refreshing when assets changed. |
| `memory/api/asset_versioning.py` | `stamp_html` | 113-130 | function | Rewrite every local asset ref's ``?v=`` to the content hash. |
| `memory/api/bulk_routes.py` | `BulkIngestItem` | 26-32 | class | A single item in a bulk ingestion request. |
| `memory/api/bulk_routes.py` | `BulkIngestRequest` | 35-45 | class | Bulk ingestion request with multiple content items. |
| `memory/api/bulk_routes.py` | `bulk_ingest` | 49-132 | async function | Ingest multiple content items in batch. |
| `memory/api/chatroom_routes.py` | `_chatroom_search_tokens` | 80-81 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_chatroom_fts_match` | 84-88 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_topic_boundary_payload` | 91-102 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_write_json_atomic` | 105-115 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_write_restart_event_marker` | 118-129 | function | Persist the restart button Marc pressed for reconnect status rows. |
| `memory/api/chatroom_routes.py` | `chatroom_root` | 134-140 | async function | Redirect the friendly chatroom URL to the static web UI. |
| `memory/api/chatroom_routes.py` | `chatroom_identity` | 144-146 | async function | Return runtime identity labels for the local instance. |
| `memory/api/chatroom_routes.py` | `chatroom_models` | 150-154 | async function | Return selectable model dropdown options from the model manifest. |
| `memory/api/chatroom_routes.py` | `chatroom_owner_session` | 158-165 | async function | Mint an SC owner session after Cloudflare Access has validated Marc. |
| `memory/api/chatroom_routes.py` | `_get_chatroom` | 168-172 | function | Get the ChatroomServer from app state. |
| `memory/api/chatroom_routes.py` | `_get_runtime_db_conn` | 175-183 | function | Return the active runtime DB connection for shared runtime tables. |
| `memory/api/chatroom_routes.py` | `_json_loads_or` | 186-195 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_normalize_room_id` | 198-200 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_row_value` | 203-207 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_collab_access_for_token` | 210-260 | async function | Async function block. |
| `memory/api/chatroom_routes.py` | `_send_collab_policy_error` | 263-264 | async function | Async function block. |
| `memory/api/chatroom_routes.py` | `_message_metadata_from_envelope` | 267-277 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_check_rate_limit` | 288-297 | function | Return True if under limit, False if rate-limited. |
| `memory/api/chatroom_routes.py` | `_buffer_decision_key` | 300-304 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_consume_buffer_decision` | 307-319 | function | Return False when this parked draft already had a decision applied. |
| `memory/api/chatroom_routes.py` | `chatroom_ws` | 326-930 | async function | WebSocket endpoint for real-time chatroom participation. |
| `memory/api/chatroom_routes.py` | `chatroom_history` | 937-949 | async function | Get recent chatroom messages. |
| `memory/api/chatroom_routes.py` | `chatroom_history_older` | 953-1063 | async function | Page the messages immediately older than `before_id` (scroll-up load-older). |
| `memory/api/chatroom_routes.py` | `chatroom_search` | 1067-1139 | async function | Search live chatroom messages across all rooms via chatroom_messages_fts. |
| `memory/api/chatroom_routes.py` | `chatroom_recent_topics` | 1143-1241 | async function | Return recent persisted topic boundaries across rooms for the Search dashboard. |
| `memory/api/chatroom_routes.py` | `_workspace_artifact_type` | 1244-1252 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_workspace_artifact_content` | 1255-1294 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_list_workspace_folder_artifacts` | 1297-1367 | function | Function block. |
| `memory/api/chatroom_routes.py` | `_merge_workspace_folder_artifacts` | 1370-1388 | function | Function block. |
| `memory/api/chatroom_routes.py` | `chatroom_artifacts` | 1393-1490 | async function | Get persisted artifacts for the Artifacts tab. |
| `memory/api/chatroom_routes.py` | `delete_artifact` | 1494-1517 | async function | Soft-delete an artifact. |
| `memory/api/chatroom_routes.py` | `restore_artifact` | 1521-1542 | async function | Restore a soft-deleted artifact. |
| `memory/api/chatroom_routes.py` | `chatroom_governance` | 1570-1656 | async function | Get unresolved governance messages for the Actions tab. |
| `memory/api/chatroom_routes.py` | `chatroom_governance_task_counts` | 1660-1686 | async function | Return unresolved Vet counts by producing task. |
| `memory/api/chatroom_routes.py` | `dismiss_chatroom_governance` | 1690-1708 | async function | Dismiss task-queue/plan_approval chatroom notifications from the Vet view. |
| `memory/api/chatroom_routes.py` | `chatroom_governance_resolved` | 1712-1801 | async function | Get resolved governance items for the audit trail. |
| `memory/api/chatroom_routes.py` | `chatroom_participants` | 1805-1810 | async function | Get current chatroom participants. |
| `memory/api/chatroom_routes.py` | `chatroom_collab_present` | 1814-1819 | async function | Return explicit room-scoped guest presence for prompt/context guards. |
| `memory/api/chatroom_routes.py` | `update_participant_statusline` | 1823-1838 | async function | Update a participant's statusline data (ctx_remaining, model_id, cc_version, cost_duration_ms). |
| `memory/api/chatroom_routes.py` | `get_nudge_file` | 1842-1861 | async function | Serve shared HOT memory content for a CC wake. |
| `memory/api/chatroom_routes.py` | `chatroom_hot_memory` | 1865-1901 | async function | Serve read-only room HOT memory content for browser visibility. |
| `memory/api/chatroom_routes.py` | `chatroom_hot_memory_notify` | 1905-1926 | async function | Notify room clients that HOT memory changed. |
| `memory/api/chatroom_routes.py` | `chatroom_topic_boundary_notify` | 1930-1966 | async function | Broadcast a freshly-written Curator topic boundary to room clients live. |
| `memory/api/chatroom_routes.py` | `chatroom_short_memory` | 1970-2006 | async function | Serve read-only room Short_Memory content for browser visibility (exact mirror of /memory/hot). |
| `memory/api/chatroom_routes.py` | `chatroom_rollup_memory` | 2010-2058 | async function | Serve the generated routed rollup view for browser visibility. |
| `memory/api/chatroom_routes.py` | `chatroom_short_memory_notify` | 2062-2083 | async function | Notify room clients that Short_Memory changed (exact mirror of hot notify). |
| `memory/api/chatroom_routes.py` | `update_nudge_file` | 2087-2100 | async function | Write per-CC Tier 0 hot memory file. |
| `memory/api/chatroom_routes.py` | `chatroom_status` | 2104-2116 | async function | Chatroom health and stats. |
| `memory/api/chatroom_routes.py` | `chatroom_debug` | 2120-2133 | async function | Cursor-paged prompt injection/drop debug log from the orchestrator. |
| `memory/api/chatroom_routes.py` | `chatroom_send` | 2137-2216 | async function | Inject a message into the chatroom from an external source. |
| `memory/api/chatroom_routes.py` | `_HighlightFeatureBody` | 2219-2224 | class | Class block. |
| `memory/api/chatroom_routes.py` | `_normalize_feature_id` | 2227-2237 | function | Function block. |
| `memory/api/chatroom_routes.py` | `post_highlight_feature` | 2241-2264 | async function | Ask the active browser UI to highlight a live feature target by stable id. |
| `memory/api/chatroom_routes.py` | `_BufferDecisionBody` | 2267-2273 | class | Class block. |
| `memory/api/chatroom_routes.py` | `buffer_decision` | 2277-2376 | async function | Handle a fresh-decision response from a CC after a parked draft window closes. |
| `memory/api/chatroom_routes.py` | `_FloorBody` | 2379-2382 | class | Class block. |
| `memory/api/chatroom_routes.py` | `get_floor` | 2386-2405 | async function | Return current pacing mode and window settings. |
| `memory/api/chatroom_routes.py` | `set_floor` | 2409-2439 | async function | Set pacing mode (off / auto / on) and optional on_seconds. |
| `memory/api/chatroom_routes.py` | `_StaggerBody` | 2442-2443 | class | Class block. |
| `memory/api/chatroom_routes.py` | `get_stagger` | 2447-2452 | async function | Return the current untagged-wake stagger delay in seconds. |
| `memory/api/chatroom_routes.py` | `set_stagger` | 2456-2465 | async function | Set the untagged-wake stagger delay (0.5-30 seconds, runtime only). |
| `memory/api/chatroom_routes.py` | `hard_refresh_notice` | 2469-2476 | async function | Record a one-shot prompt notice before the browser hard-refreshes. |
| `memory/api/chatroom_routes.py` | `kick_collab` | 2480-2496 | async function | Kick a guest by participant_id. |
| `memory/api/chatroom_routes.py` | `restart_cc` | 2500-2519 | async function | Remote-restart a CC's orchestrator. |
| `memory/api/chatroom_routes.py` | `get_collab_activity` | 2525-2559 | async function | Return guest activity log: joins, leaves, messages, tab switches. |
| `memory/api/chatroom_routes.py` | `_ReactionBody` | 2564-2566 | class | Class block. |
| `memory/api/chatroom_routes.py` | `toggle_reaction` | 2570-2601 | async function | Toggle an emoji reaction on a message (adds if not present, removes if already reacted). |
| `memory/api/chatroom_routes.py` | `get_reactions` | 2605-2611 | async function | Get all reactions for a specific message. |
| `memory/api/chatroom_routes.py` | `get_bulk_reactions` | 2615-2621 | async function | Get reactions for multiple messages at once. |
| `memory/api/chatroom_routes.py` | `get_recent_reactions` | 2625-2687 | async function | Return recent reactions joined with the message they were attached to. |
| `memory/api/chatroom_routes.py` | `get_feedback_calibration` | 2691-2745 | async function | Return short-lived style calibration for one agent from feedback_events. |
| `memory/api/chatroom_routes.py` | `list_feedback_preferences` | 2749-2812 | async function | List synthesized feedback preference rows. |
| `memory/api/chatroom_routes.py` | `synthesize_feedback_preferences_route` | 2816-2824 | async function | Dry-run or apply durable feedback preference synthesis. |
| `memory/api/chatroom_routes.py` | `_TurnSignalBody` | 2827-2829 | class | Class block. |
| `memory/api/chatroom_routes.py` | `post_turn_signal` | 2833-2839 | async function | Broadcast a turn-level signal (e.g. |
| `memory/api/chatroom_routes.py` | `_AiReceiptBody` | 2842-2847 | class | Class block. |
| `memory/api/chatroom_routes.py` | `_persist_ai_seen_receipt` | 2850-2903 | async function | Async function block. |
| `memory/api/chatroom_routes.py` | `post_ai_receipt` | 2907-2976 | async function | Broadcast a UI-only receipt when an AI actually receives a message. |
| `memory/api/chatroom_routes.py` | `restart_chatroom` | 2982-3027 | async function | Full restart of all Structured Chaos processes to pick up code changes. |
| `memory/api/chatroom_routes.py` | `shutdown_chatroom` | 3031-3056 | async function | Stop ALL Structured Chaos processes (the product's off switch). |
| `memory/api/chatroom_routes.py` | `restart_api_only` | 3060-3086 | async function | Restart the API process and ensure the PMS v2 sidecar dependency is alive. |
| `memory/api/chatroom_routes.py` | `recycle_agent` | 3090-3109 | async function | Recycle one agent in one room (the master tray's per-agent Recycle). |
| `memory/api/chatroom_routes.py` | `_HostSelfieFanoutRequest` | 3114-3115 | class | Class block. |
| `memory/api/chatroom_routes.py` | `_fanout_host_selfie` | 3118-3142 | async function | Inject a system message with the host selfie attachment so all CCs see the image. |
| `memory/api/chatroom_routes.py` | `upload_host_selfie` | 3146-3205 | async function | Marc uploads a selfie for roast mode. |
| `memory/api/chatroom_routes.py` | `fanout_host_selfie` | 3209-3215 | async function | Re-fanout an already-uploaded selfie URL (for cached re-use across mode flips). |
| `memory/api/claim_routes.py` | `_normalize_task_label` | 33-34 | function | Function block. |
| `memory/api/claim_routes.py` | `_stem` | 37-45 | function | Function block. |
| `memory/api/claim_routes.py` | `_significant_tokens` | 48-51 | function | Function block. |
| `memory/api/claim_routes.py` | `_has_shared_phrase` | 54-65 | function | Function block. |
| `memory/api/claim_routes.py` | `_task_labels_collide` | 68-85 | function | Function block. |
| `memory/api/claim_routes.py` | `_registry_key` | 88-89 | function | Function block. |
| `memory/api/claim_routes.py` | `_expire` | 92-96 | function | Function block. |
| `memory/api/claim_routes.py` | `ClaimRequest` | 99-102 | class | Class block. |
| `memory/api/claim_routes.py` | `register_claim` | 106-127 | function | Function block. |
| `memory/api/claim_routes.py` | `release_claim` | 131-134 | function | Function block. |
| `memory/api/claim_routes.py` | `active_claims` | 138-150 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueItemCreateRequest` | 35-46 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueLeaseRequest` | 49-55 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueHeartbeatRequest` | 58-60 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueRunningRequest` | 63-64 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueCompleteRequest` | 67-72 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `ClaimQueueDispatchRequest` | 75-78 | class | Class block. |
| `memory/api/claims_queue_routes.py` | `_register` | 81-87 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_claims_queue_db_path` | 90-99 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_run_store` | 102-110 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `_item_payload` | 113-114 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_publish_update` | 117-135 | async function | Best-effort live notification; a publish failure never fails the request. |
| `memory/api/claims_queue_routes.py` | `_schedule_auto_pickup_advance` | 138-170 | function | Best-effort Auto Pick-Up re-ignite; never fail the queue mutation. |
| `memory/api/claims_queue_routes.py` | `_maybe_schedule_auto_pickup_advance` | 173-185 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_http_from_store_error` | 188-193 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_claim_line` | 196-197 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `_enqueue_fuzzy_duplicate_wake` | 200-245 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `create_item` | 249-304 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `list_items` | 308-334 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `get_item` | 338-342 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `lease_item` | 346-371 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `release_item_lease` | 375-381 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `heartbeat_item` | 385-394 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `running_item` | 398-406 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `complete_item` | 410-445 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `reject_item` | 449-455 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `cancel_item` | 459-465 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `stale_item` | 469-475 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `reap_leases` | 479-483 | async function | Async function block. |
| `memory/api/claims_queue_routes.py` | `_chatroom_server` | 486-489 | function | Function block. |
| `memory/api/claims_queue_routes.py` | `dispatch` | 493-534 | async function | Lease a pending item to one agent and announce the execution_dispatch wake. |
| `memory/api/codebase_routes.py` | `HumanEditRequest` | 52-57 | class | Class block. |
| `memory/api/codebase_routes.py` | `RepoCreateRequest` | 60-63 | class | Class block. |
| `memory/api/codebase_routes.py` | `RepoUpdateRequest` | 66-68 | class | Class block. |
| `memory/api/codebase_routes.py` | `ProtectedDiffRevertRequest` | 71-72 | class | Class block. |
| `memory/api/codebase_routes.py` | `_resolve_slug` | 75-76 | function | Function block. |
| `memory/api/codebase_routes.py` | `_decorate_repo` | 79-82 | function | Function block. |
| `memory/api/codebase_routes.py` | `_strip_diff_history_bodies` | 85-104 | function | Remove full diff bodies from visual history while preserving metadata. |
| `memory/api/codebase_routes.py` | `_diff_paths` | 107-119 | function | Function block. |
| `memory/api/codebase_routes.py` | `_read_text_or_empty` | 122-128 | function | Function block. |
| `memory/api/codebase_routes.py` | `_reverse_single_file_unified_diff` | 131-180 | function | Function block. |
| `memory/api/codebase_routes.py` | `list_codebase_repos` | 184-189 | async function | Return every selectable repo for the Codebase tab dropdown. |
| `memory/api/codebase_routes.py` | `add_codebase_repo` | 193-199 | async function | Async function block. |
| `memory/api/codebase_routes.py` | `update_codebase_repo` | 203-213 | async function | Async function block. |
| `memory/api/codebase_routes.py` | `delete_codebase_repo` | 217-224 | async function | Async function block. |
| `memory/api/codebase_routes.py` | `get_file` | 228-241 | async function | Return file content + structural sections from `_INDEX.md` block maps. |
| `memory/api/codebase_routes.py` | `get_section_summary` | 245-254 | async function | Return sections + per-section edit counts (drives gutter chips). |
| `memory/api/codebase_routes.py` | `get_diffs_for_file` | 258-284 | async function | Return chronological (newest first) diff events for a file. |
| `memory/api/codebase_routes.py` | `get_full_diff_event` | 288-304 | async function | Return one uncapped diff event for deliberate, user-requested expansion. |
| `memory/api/codebase_routes.py` | `revert_protected_diff_event` | 308-401 | async function | Reverse-apply one protected file diff and emit a tracked revert diff. |
| `memory/api/codebase_routes.py` | `get_diffs_for_section` | 405-421 | async function | Return chronological (newest first) diff events touching one section. |
| `memory/api/codebase_routes.py` | `list_recently_edited_files` | 425-462 | async function | List files with recent diff activity (newest first), with edit counts. |
| `memory/api/codebase_routes.py` | `post_file_edit` | 466-524 | async function | Write a human edit and emit a `file_diff` activity event. |
| `memory/api/codebase_routes.py` | `get_authors` | 528-551 | async function | Return ``{authors, version}`` mapping every known author to a stable color. |
| `memory/api/codebase_routes.py` | `get_author_color` | 555-559 | async function | Return color metadata for a single agent string (curated or hashed). |
| `memory/api/codebase_routes.py` | `PreferenceWrite` | 562-563 | class | Class block. |
| `memory/api/codebase_routes.py` | `list_preferences` | 567-569 | async function | Return every persisted UI preference plus defaults for missing keys. |
| `memory/api/codebase_routes.py` | `get_preference_route` | 573-578 | async function | Return a single preference by namespaced key (e.g. |
| `memory/api/codebase_routes.py` | `post_preference_route` | 582-587 | async function | Upsert a preference value for ``key``. |
| `memory/api/codespace_routes.py` | `CreateDocRequest` | 29-32 | class | Class block. |
| `memory/api/codespace_routes.py` | `EditDocRequest` | 34-38 | class | Class block. |
| `memory/api/codespace_routes.py` | `ReplaceDocRequest` | 40-43 | class | Class block. |
| `memory/api/codespace_routes.py` | `_get_conn` | 50-60 | function | Return the live PMS v2 runtime connection, or 503 if unavailable. |
| `memory/api/codespace_routes.py` | `_broadcast_codespace` | 63-73 | async function | Broadcast codespace update to all WebSocket clients. |
| `memory/api/codespace_routes.py` | `_snapshot_version` | 76-92 | async function | Save a version snapshot for undo/history. |
| `memory/api/codespace_routes.py` | `list_documents` | 100-114 | async function | List all codespace documents. |
| `memory/api/codespace_routes.py` | `get_document` | 118-133 | async function | Get a document with full content. |
| `memory/api/codespace_routes.py` | `create_document` | 137-157 | async function | Create a new codespace document. |
| `memory/api/codespace_routes.py` | `edit_document` | 161-211 | async function | Apply an old_text/new_text patch to a document (CC-style edit). |
| `memory/api/codespace_routes.py` | `replace_document` | 215-254 | async function | Full content replace (for browser saves). |
| `memory/api/codespace_routes.py` | `delete_document` | 258-271 | async function | Delete a codespace document and its version history. |
| `memory/api/codespace_routes.py` | `list_versions` | 275-288 | async function | List version history for a document. |
| `memory/api/codespace_routes.py` | `revert_to_version` | 292-332 | async function | Revert a document to a specific version. |
| `memory/api/codespace_routes.py` | `read_repo_file` | 346-367 | async function | Read a file from the SC repo root. |
| `memory/api/codespace_routes.py` | `list_repo_dir` | 371-394 | async function | List files in a repo directory. |
| `memory/api/collab_routes.py` | `_get_hub` | 32-37 | function | Function block. |
| `memory/api/collab_routes.py` | `_static_path` | 40-41 | function | Function block. |
| `memory/api/collab_routes.py` | `CreateCollabInviteRequest` | 44-57 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabJoinRequest` | 60-65 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabNotesRequest` | 68-69 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabMessageRequest` | 72-73 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabFloorRequest` | 76-78 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabExtendRequest` | 81-82 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabPauseRequest` | 85-86 | class | Class block. |
| `memory/api/collab_routes.py` | `CollabTabAccessRequest` | 89-90 | class | Class block. |
| `memory/api/collab_routes.py` | `collab_modes` | 94-95 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_tab_access_options` | 99-100 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_admin_page` | 104-108 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_entry_page` | 112-121 | async function | Async function block. |
| `memory/api/collab_routes.py` | `get_collab_invite` | 125-130 | async function | Async function block. |
| `memory/api/collab_routes.py` | `list_collab_invites` | 134-136 | async function | Async function block. |
| `memory/api/collab_routes.py` | `create_collab_invite` | 140-170 | async function | Async function block. |
| `memory/api/collab_routes.py` | `revoke_collab_invite` | 174-180 | async function | Async function block. |
| `memory/api/collab_routes.py` | `join_collab_invite` | 184-217 | async function | Async function block. |
| `memory/api/collab_routes.py` | `_collab_cookie_max_age` | 220-232 | function | Seconds until the invite expires, or None for a session cookie. |
| `memory/api/collab_routes.py` | `collab_public_api_proxy` | 262-279 | async function | Route collaborator API calls through a Cloudflare-bypassed guest path. |
| `memory/api/collab_routes.py` | `_collab_proxy_target_is_allowed` | 282-286 | function | Function block. |
| `memory/api/collab_routes.py` | `_query_with_guest_token` | 289-296 | function | Function block. |
| `memory/api/collab_routes.py` | `_collab_proxy_scope` | 299-316 | function | Function block. |
| `memory/api/collab_routes.py` | `_collab_proxy_headers` | 319-345 | function | Function block. |
| `memory/api/collab_routes.py` | `_collab_proxy_policy_allows` | 348-355 | async function | Async function block. |
| `memory/api/collab_routes.py` | `_collab_stream_internal_request` | 358-412 | async function | Async function block. |
| `memory/api/collab_routes.py` | `_collab_proxy_response_headers` | 415-425 | function | Function block. |
| `memory/api/collab_routes.py` | `upload_collab_selfie` | 429-480 | async function | Async function block. |
| `memory/api/collab_routes.py` | `upload_collab_avatar` | 484-511 | async function | Async function block. |
| `memory/api/collab_routes.py` | `guest_overview` | 515-516 | async function | Async function block. |
| `memory/api/collab_routes.py` | `list_collabs` | 520-522 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_detail` | 526-531 | async function | Async function block. |
| `memory/api/collab_routes.py` | `update_collab_notes` | 535-543 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_session_detail` | 547-553 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_session_prompts` | 557-562 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_session_messages` | 566-572 | async function | Async function block. |
| `memory/api/collab_routes.py` | `approve_collab_session` | 576-582 | async function | Async function block. |
| `memory/api/collab_routes.py` | `reject_collab_session` | 586-592 | async function | Async function block. |
| `memory/api/collab_routes.py` | `send_collab_host_message` | 596-605 | async function | Async function block. |
| `memory/api/collab_routes.py` | `set_collab_session_floor` | 609-621 | async function | Async function block. |
| `memory/api/collab_routes.py` | `extend_collab_session` | 625-634 | async function | Async function block. |
| `memory/api/collab_routes.py` | `pause_collab_session` | 638-647 | async function | Async function block. |
| `memory/api/collab_routes.py` | `update_collab_session_tab_access` | 651-660 | async function | Async function block. |
| `memory/api/collab_routes.py` | `CollabAccessResolveRequest` | 663-664 | class | Class block. |
| `memory/api/collab_routes.py` | `resolve_collab_access_request` | 668-677 | async function | Host approves (grant applied) or denies a guest's access-extension request. |
| `memory/api/collab_routes.py` | `end_collab_session` | 681-687 | async function | Async function block. |
| `memory/api/collab_routes.py` | `send_collab_transcript_email` | 691-697 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_ws` | 701-711 | async function | Async function block. |
| `memory/api/collab_routes.py` | `collab_admin_ws` | 715-720 | async function | Async function block. |
| `memory/api/conversation_routes.py` | `_connect` | 13-17 | function | Function block. |
| `memory/api/conversation_routes.py` | `_search_conversations_sync` | 20-173 | function | Function block. |
| `memory/api/conversation_routes.py` | `search_conversations` | 177-191 | async function | Async function block. |
| `memory/api/conversation_routes.py` | `conversation_stats` | 195-226 | async function | Async function block. |
| `memory/api/current_situation_routes.py` | `PhoneLocationUpdate` | 20-26 | class | Class block. |
| `memory/api/current_situation_routes.py` | `_configured_update_token` | 29-30 | function | Function block. |
| `memory/api/current_situation_routes.py` | `_bearer_token` | 33-39 | function | Function block. |
| `memory/api/current_situation_routes.py` | `_verify_location_update_token` | 42-56 | function | Function block. |
| `memory/api/current_situation_routes.py` | `_arrived_via_cloudflare` | 59-60 | function | Function block. |
| `memory/api/current_situation_routes.py` | `get_current_situation` | 64-72 | async function | Async function block. |
| `memory/api/current_situation_routes.py` | `update_current_location` | 76-83 | async function | Async function block. |
| `memory/api/db_browser_routes.py` | `_quote_ident` | 55-56 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_connect_readonly` | 59-67 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_is_internal_table` | 70-79 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_table_rows` | 82-91 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_columns_for` | 94-106 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_indexes_for` | 109-129 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_is_text_column` | 132-142 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_like_pattern` | 145-147 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_stringify` | 150-158 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_snippet` | 161-169 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_pick_title` | 172-178 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_pick_timestamp` | 181-186 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_row_payload` | 189-195 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_matching_columns` | 198-208 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_order_clause` | 211-215 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_validated_order_clause` | 218-230 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_table_count` | 233-238 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_validate_table` | 241-258 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_row_result` | 261-271 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_search_table` | 274-306 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_split_csv` | 309-312 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_filter_clauses` | 315-372 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_browse_table` | 375-443 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_schema_for_db` | 446-478 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_schema_error_for_db` | 481-491 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_schemas_for_all_databases` | 494-503 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_search_database` | 506-558 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_table_exists` | 561-566 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_column_names` | 569-573 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_fetch_related_section` | 576-591 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_related_records` | 594-668 | function | Function block. |
| `memory/api/db_browser_routes.py` | `DbSqlRequest` | 671-674 | class | Class block. |
| `memory/api/db_browser_routes.py` | `_normalize_safe_sql` | 677-694 | function | Function block. |
| `memory/api/db_browser_routes.py` | `_run_readonly_sql` | 697-734 | function | Function block. |
| `memory/api/db_browser_routes.py` | `db_browser_schema` | 738-742 | async function | Return searchable databases and table/column metadata. |
| `memory/api/db_browser_routes.py` | `db_browser_search` | 746-754 | async function | Search text columns in known local SQLite databases. |
| `memory/api/db_browser_routes.py` | `db_browser_table` | 758-788 | async function | Browse rows from one known SQLite table. |
| `memory/api/db_browser_routes.py` | `db_browser_related` | 792-799 | async function | Find obvious related rows for a record id. |
| `memory/api/db_browser_routes.py` | `db_browser_sql` | 803-805 | async function | Run constrained read-only SQL against a known local database. |
| `memory/api/db_browser_routes.py` | `_db_disk_size` | 808-817 | function | Total on-disk footprint: main db plus the -wal/-shm sidecars. |
| `memory/api/db_browser_routes.py` | `db_browser_stats` | 821-841 | function | Live size + reclaimable-space readout for the DB tab. |
| `memory/api/db_browser_routes.py` | `db_browser_vacuum` | 845-884 | async function | Compact the database: VACUUM reclaims free space left by deletions and the ring-buffer caps, rewriting the file. |
| `memory/api/email_routes.py` | `EmailIngestRequest` | 16-20 | class | Request to ingest a specific email by UID. |
| `memory/api/email_routes.py` | `EmailSearchRequest` | 23-28 | class | Request to search emails. |
| `memory/api/email_routes.py` | `_check_email` | 31-41 | function | Guard: ensure email connector is initialized. |
| `memory/api/email_routes.py` | `email_status` | 45-48 | async function | Check email connection status. |
| `memory/api/email_routes.py` | `email_folders` | 52-56 | async function | List available email folders. |
| `memory/api/email_routes.py` | `email_recent` | 60-70 | async function | Fetch recent email summaries. |
| `memory/api/email_routes.py` | `email_detail` | 74-83 | async function | Fetch a single email with full content. |
| `memory/api/email_routes.py` | `email_search` | 87-95 | async function | Search emails by subject or sender. |
| `memory/api/email_routes.py` | `email_ingest` | 99-111 | async function | Ingest a specific email into PMS memory. |
| `memory/api/file_routes.py` | `_png_to_jpeg` | 48-65 | function | Convert PNG bytes to JPEG at 85% quality. |
| `memory/api/file_routes.py` | `_normalize_room` | 68-73 | function | Function block. |
| `memory/api/file_routes.py` | `_transfers_dir` | 76-83 | function | Transfer storage dir for a room. |
| `memory/api/file_routes.py` | `_entry_transfers_dir` | 86-88 | function | Function block. |
| `memory/api/file_routes.py` | `_ensure_dir` | 91-94 | function | Function block. |
| `memory/api/file_routes.py` | `_migrate_legacy_manifest` | 97-116 | function | Lazily rename a pre-existing legacy ``<name>.json`` to the current extensionless ``MANIFEST_PATH`` on first access. |
| `memory/api/file_routes.py` | `_load_manifest` | 119-126 | function | Function block. |
| `memory/api/file_routes.py` | `_replace_manifest_file` | 129-130 | function | Function block. |
| `memory/api/file_routes.py` | `_save_manifest` | 133-155 | function | Function block. |
| `memory/api/file_routes.py` | `_safe_object_name` | 158-161 | function | Function block. |
| `memory/api/file_routes.py` | `_transfer_object_key` | 164-170 | function | Function block. |
| `memory/api/file_routes.py` | `_entry_r2_object_key` | 173-177 | function | Function block. |
| `memory/api/file_routes.py` | `_put_transfer_object` | 180-186 | async function | Async function block. |
| `memory/api/file_routes.py` | `_delete_transfer_object` | 189-191 | async function | Async function block. |
| `memory/api/file_routes.py` | `_ensure_transfer_r2_object` | 194-217 | async function | Async function block. |
| `memory/api/file_routes.py` | `_resolve_generated_media` | 220-233 | function | Function block. |
| `memory/api/file_routes.py` | `_resolve_generated_image` | 236-240 | function | Function block. |
| `memory/api/file_routes.py` | `files_ui` | 244-248 | async function | Async function block. |
| `memory/api/file_routes.py` | `upload_files` | 252-318 | async function | Async function block. |
| `memory/api/file_routes.py` | `list_files` | 322-326 | async function | Async function block. |
| `memory/api/file_routes.py` | `file_info` | 330-336 | async function | Async function block. |
| `memory/api/file_routes.py` | `_resize_avatar` | 354-367 | function | Function block. |
| `memory/api/file_routes.py` | `_is_valid_avatar_participant` | 370-371 | function | Function block. |
| `memory/api/file_routes.py` | `save_avatar_image` | 374-385 | function | Function block. |
| `memory/api/file_routes.py` | `_resize_background` | 388-401 | function | Function block. |
| `memory/api/file_routes.py` | `upload_avatar` | 405-415 | async function | Async function block. |
| `memory/api/file_routes.py` | `get_avatar` | 419-429 | async function | Async function block. |
| `memory/api/file_routes.py` | `upload_default_background` | 433-446 | async function | Async function block. |
| `memory/api/file_routes.py` | `get_default_background` | 450-454 | async function | Async function block. |
| `memory/api/file_routes.py` | `generated_image` | 458-466 | async function | Serve allowlisted generated images from workspace media or legacy Codex output. |
| `memory/api/file_routes.py` | `generated_media` | 470-478 | async function | Serve allowlisted generated images/videos from workspace media or legacy Codex output. |
| `memory/api/file_routes.py` | `file_download_url` | 482-505 | async function | Async function block. |
| `memory/api/file_routes.py` | `download_file` | 509-523 | async function | Async function block. |
| `memory/api/file_routes.py` | `append_to_file` | 531-553 | async function | Append raw text body to a project file. |
| `memory/api/file_routes.py` | `delete_all_files` | 557-580 | async function | Async function block. |
| `memory/api/file_routes.py` | `delete_file` | 584-604 | async function | Async function block. |
| `memory/api/governance_routes.py` | `get_escalations_gone` | 44-50 | async function | Deprecated — governance removed. |
| `memory/api/governance_routes.py` | `resolve_escalation_gone` | 54-59 | async function | Deprecated — governance removed. |
| `memory/api/governance_routes.py` | `submit_and_wait_gone` | 63-65 | async function | Deprecated — governance and the change-log write path are both removed. |
| `memory/api/governance_routes.py` | `get_pending_approvals_gone` | 69-71 | async function | Deprecated — governance removed. |
| `memory/api/governance_routes.py` | `list_task_scopes_gone` | 75-77 | async function | Deprecated — governance removed. |
| `memory/api/governance_routes.py` | `lifecycle_report_gone` | 81-86 | async function | Deprecated — lifecycle removed. |
| `memory/api/governance_routes.py` | `trigger_maintenance_gone` | 90-92 | async function | Deprecated — lifecycle removed. |
| `memory/api/governance_routes.py` | `scheduler_status` | 99-103 | async function | View the background scheduler's current status. |
| `memory/api/governance_routes.py` | `scheduler_trigger` | 107-125 | async function | Manually trigger a scheduler task. |
| `memory/api/ingest_routes.py` | `TranscriptIngestRequest` | 36-41 | class | Payload sent by Anvil's transcript sync daemon. |
| `memory/api/ingest_routes.py` | `SubprocessOutputRequest` | 44-49 | class | Log subprocess output to conversation_messages (LONG tier). |
| `memory/api/ingest_routes.py` | `ingest_subprocess_output` | 53-58 | async function | Log subprocess output to LONG tier. |
| `memory/api/ingest_routes.py` | `_load_manifest` | 67-73 | function | Function block. |
| `memory/api/ingest_routes.py` | `_run_ingest` | 76-139 | async function | Parse and ingest a single file. |
| `memory/api/ingest_routes.py` | `ingest_transcript` | 143-193 | async function | Ingest a transcript posted directly by Anvil's sync daemon. |
| `memory/api/ingest_routes.py` | `ingest_remote` | 197-246 | async function | Ingest a file uploaded from Anvil into PMS memory. |
| `memory/api/ingest_routes.py` | `ingest_remote_sync` | 250-290 | async function | Synchronous variant — waits for ingestion to complete and returns result. |
| `memory/api/invite_routes.py` | `_get_chatroom` | 42-44 | function | Function block. |
| `memory/api/invite_routes.py` | `_get_db` | 47-56 | function | Function block. |
| `memory/api/invite_routes.py` | `_get_settings` | 59-61 | function | Function block. |
| `memory/api/invite_routes.py` | `_validate_admin` | 64-70 | function | Admin validation — LAN-only access, no token needed. |
| `memory/api/invite_routes.py` | `_sanitize_name` | 73-87 | function | Strip dangerous chars, enforce length. |
| `memory/api/invite_routes.py` | `_sanitize_email` | 90-97 | function | Lowercase, strip, basic format check. |
| `memory/api/invite_routes.py` | `_now_iso` | 100-101 | function | Function block. |
| `memory/api/invite_routes.py` | `_expires_iso` | 104-106 | function | Function block. |
| `memory/api/invite_routes.py` | `_parse_iso` | 109-110 | function | Function block. |
| `memory/api/invite_routes.py` | `CreateInviteRequest` | 117-119 | class | Class block. |
| `memory/api/invite_routes.py` | `JoinRequest` | 122-128 | class | Class block. |
| `memory/api/invite_routes.py` | `create_invite` | 136-172 | async function | Generate a new invite token. |
| `memory/api/invite_routes.py` | `list_invites` | 176-210 | async function | List active (non-expired, non-revoked) invites. |
| `memory/api/invite_routes.py` | `list_collab_profiles` | 214-240 | async function | List all guest profiles with visit counts. |
| `memory/api/invite_routes.py` | `invite_landing` | 244-246 | async function | Serve the guest landing page. |
| `memory/api/invite_routes.py` | `join_chatroom` | 250-333 | async function | Validate token and register guest. |
| `memory/api/invite_routes.py` | `upload_selfie` | 337-410 | async function | Accept a selfie upload for Roast mode. |
| `memory/api/invite_routes.py` | `kick_collab` | 414-441 | async function | Kick a guest: close their WS + revoke token. |
| `memory/api/invite_routes.py` | `NotesRequest` | 448-449 | class | Class block. |
| `memory/api/invite_routes.py` | `get_collab_profile` | 453-486 | async function | Get full guest profile with visit history. |
| `memory/api/invite_routes.py` | `get_collab_chat_history` | 490-537 | async function | Get chat messages from a guest's visit(s). |
| `memory/api/invite_routes.py` | `update_collab_notes` | 541-560 | async function | Update Marc's notes on a guest profile. |
| `memory/api/mcp_routes.py` | `verify_mcp_auth` | 44-63 | async function | Check Bearer token if MEMORY_MCP_API_KEY is configured. |
| `memory/api/mcp_routes.py` | `_create_tool_handler` | 68-87 | function | Create an MCPToolHandler using FastAPI app_state services. |
| `memory/api/mcp_routes.py` | `sse_connect` | 93-142 | async function | SSE connection endpoint — opens an event stream for a new session. |
| `memory/api/mcp_routes.py` | `sse_message` | 148-218 | async function | Receive a JSON-RPC message and route the response to the SSE stream. |
| `memory/api/mcp_routes.py` | `list_sessions` | 224-229 | async function | List active MCP SSE sessions (for debugging). |
| `memory/api/monitor_routes.py` | `_require_lan` | 34-43 | function | Raise 403 for public monitor requests not already validated upstream. |
| `memory/api/monitor_routes.py` | `_info_to_dict` | 50-62 | function | Convert SubprocessInfo dataclass to a JSON-serialisable dict. |
| `memory/api/monitor_routes.py` | `_normalize_subprocess_payload` | 65-74 | function | Function block. |
| `memory/api/monitor_routes.py` | `_normalize_room_id` | 90-92 | function | Function block. |
| `memory/api/monitor_routes.py` | `_participant_snapshot` | 95-104 | function | Function block. |
| `memory/api/monitor_routes.py` | `_reported_age_seconds` | 107-112 | function | Function block. |
| `memory/api/monitor_routes.py` | `_is_shared_subprocess` | 115-118 | function | Function block. |
| `memory/api/monitor_routes.py` | `_shared_key` | 121-125 | function | Function block. |
| `memory/api/monitor_routes.py` | `_dedupe_shared_subprocesses` | 128-153 | function | Function block. |
| `memory/api/monitor_routes.py` | `_snapshot_to_dict` | 156-181 | function | Function block. |
| `memory/api/monitor_routes.py` | `_empty_monitor_payload` | 184-197 | function | Function block. |
| `memory/api/monitor_routes.py` | `_session_attr` | 200-203 | function | Function block. |
| `memory/api/monitor_routes.py` | `_short_session` | 206-215 | function | Function block. |
| `memory/api/monitor_routes.py` | `_seconds_label` | 218-229 | function | Function block. |
| `memory/api/monitor_routes.py` | `_build_thinker_status_row` | 232-365 | async function | Expose the current API-owned Thinker session worker in monitor status. |
| `memory/api/monitor_routes.py` | `_append_thinker_status_row` | 368-388 | function | Function block. |
| `memory/api/monitor_routes.py` | `_schedule_chatroom_participant_refresh` | 391-397 | function | Function block. |
| `memory/api/monitor_routes.py` | `monitor_status` | 405-417 | async function | Return the latest monitor snapshot for all participants. |
| `memory/api/monitor_routes.py` | `vector_embedding_status` | 421-448 | async function | Return retired vector embedding status. |
| `memory/api/monitor_routes.py` | `ParticipantReport` | 451-454 | class | Class block. |
| `memory/api/monitor_routes.py` | `participant_report` | 458-489 | async function | Receive subprocess state report from a chatroom participant. |
| `memory/api/monitor_routes.py` | `get_prompt` | 494-507 | async function | Read a prompt file by subprocess name. |
| `memory/api/monitor_routes.py` | `PromptUpdate` | 510-511 | class | Class block. |
| `memory/api/monitor_routes.py` | `update_prompt` | 515-527 | async function | Write edited prompt content back to disk. |
| `memory/api/monitor_routes.py` | `get_log` | 531-547 | async function | Return the last N lines of a subprocess log file. |
| `memory/api/monitor_routes.py` | `_snapshot_processes_for_room` | 554-560 | function | Function block. |
| `memory/api/monitor_routes.py` | `_resolve_prompt_path` | 563-579 | function | Map a subprocess name (slug or role) to its prompt file path. |
| `memory/api/monitor_routes.py` | `_resolve_log_path` | 582-598 | function | Map a subprocess name (slug or role) to its log file path. |
| `memory/api/monitor_routes.py` | `_hot_size_files_for_room` | 616-625 | function | Function block. |
| `memory/api/monitor_routes.py` | `_count_hot_items` | 634-640 | function | Count bullet items (lines starting with `* [`) in a tracked HOT-size file. |
| `memory/api/monitor_routes.py` | `_prune_hot_size_samples` | 643-645 | function | Function block. |
| `memory/api/monitor_routes.py` | `_ensure_hot_table` | 648-673 | function | Function block. |
| `memory/api/monitor_routes.py` | `_sample_hot_sizes` | 676-701 | function | Read tracked HOT-size files now; persist to DB if rate-limit allows. |
| `memory/api/monitor_routes.py` | `hot_size_current` | 712-717 | async function | Return current HOT file item counts. |
| `memory/api/monitor_routes.py` | `hot_size_history` | 721-748 | async function | Return historical samples grouped by file. |
| `memory/api/notepad_routes.py` | `NoteWriteRequest` | 28-30 | class | Class block. |
| `memory/api/notepad_routes.py` | `NoteFormatRequest` | 33-34 | class | Class block. |
| `memory/api/notepad_routes.py` | `NoteImportRequest` | 37-39 | class | Class block. |
| `memory/api/notepad_routes.py` | `_format_prompt` | 56-67 | function | Function block. |
| `memory/api/notepad_routes.py` | `_slug_name` | 70-73 | function | Function block. |
| `memory/api/notepad_routes.py` | `_notes_root` | 76-84 | function | Function block. |
| `memory/api/notepad_routes.py` | `_room_id` | 87-91 | function | Function block. |
| `memory/api/notepad_routes.py` | `_resolve_note_path` | 94-112 | function | Function block. |
| `memory/api/notepad_routes.py` | `_note_imports_path` | 115-117 | function | Function block. |
| `memory/api/notepad_routes.py` | `_import_key` | 120-121 | function | Function block. |
| `memory/api/notepad_routes.py` | `_now_iso` | 124-125 | function | Function block. |
| `memory/api/notepad_routes.py` | `_clean_import_ref` | 128-144 | function | Function block. |
| `memory/api/notepad_routes.py` | `_load_import_refs` | 147-168 | function | Function block. |
| `memory/api/notepad_routes.py` | `_save_import_refs` | 171-174 | function | Function block. |
| `memory/api/notepad_routes.py` | `_note_payload` | 177-185 | function | Function block. |
| `memory/api/notepad_routes.py` | `_import_payload` | 188-210 | function | Function block. |
| `memory/api/notepad_routes.py` | `list_notes` | 214-224 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `import_note` | 228-244 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `remove_imported_note` | 248-263 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `read_note` | 267-274 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `save_note` | 278-286 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `create_note` | 290-311 | async function | Async function block. |
| `memory/api/notepad_routes.py` | `format_note` | 315-346 | async function | Async function block. |
| `memory/api/provider_routes.py` | `_provider_installed` | 55-60 | function | Function block. |
| `memory/api/provider_routes.py` | `_status_for` | 63-78 | function | Function block. |
| `memory/api/provider_routes.py` | `providers_status` | 82-86 | async function | Per-provider {installed, signed_in, setup progress}. |
| `memory/api/provider_routes.py` | `_set_state` | 89-91 | function | Function block. |
| `memory/api/provider_routes.py` | `_run_setup` | 94-136 | function | Background worker: install the CLI if missing, then sign in. |
| `memory/api/provider_routes.py` | `provider_setup` | 140-156 | async function | Install the provider CLI if missing, then start its login flow. |
| `memory/api/provider_routes.py` | `provider_api_key` | 160-180 | async function | Store an API key in .env for the API-key door of the same window. |
| `memory/api/public_access_guard.py` | `PublicAccessGuardMiddleware` | 66-129 | class | Block public access to owner/API surfaces unless owner-authenticated. |
| `memory/api/public_access_guard.py` | `PublicAccessGuardMiddleware.__init__` | 69-70 | method | Method block. |
| `memory/api/public_access_guard.py` | `PublicAccessGuardMiddleware.__call__` | 72-129 | async method | Async method block. |
| `memory/api/public_access_guard.py` | `is_public_request` | 132-148 | function | Return True when a request must pass public auth (Cloudflare Access, owner token, or the guest allowlist) rather than the trusted-LAN bypass. |
| `memory/api/public_access_guard.py` | `_client_ip` | 151-158 | function | Function block. |
| `memory/api/public_access_guard.py` | `_peer_is_trusted` | 161-171 | function | True only for a genuinely local/LAN TCP peer. |
| `memory/api/public_access_guard.py` | `owner_token_valid` | 174-181 | function | Function block. |
| `memory/api/public_access_guard.py` | `owner_session_cookie_valid` | 184-188 | function | Function block. |
| `memory/api/public_access_guard.py` | `mint_owner_session_cookie` | 191-201 | function | Function block. |
| `memory/api/public_access_guard.py` | `owner_session_cookie_header` | 204-209 | function | Function block. |
| `memory/api/public_access_guard.py` | `_owner_session_payload` | 212-223 | function | Function block. |
| `memory/api/public_access_guard.py` | `_decode_owner_session_cookie` | 226-245 | function | Function block. |
| `memory/api/public_access_guard.py` | `_owner_session_signature` | 248-253 | function | Function block. |
| `memory/api/public_access_guard.py` | `_b64url_encode` | 256-259 | function | Function block. |
| `memory/api/public_access_guard.py` | `_b64url_decode` | 262-265 | function | Function block. |
| `memory/api/public_access_guard.py` | `cloudflare_owner_chatroom_valid` | 268-277 | async function | Allow Cloudflare Access-verified owner identity on chat UI surfaces only. |
| `memory/api/public_access_guard.py` | `_cloudflare_owner_access_result` | 280-284 | function | Function block. |
| `memory/api/public_access_guard.py` | `_cloudflare_owner_access_result_inner` | 287-311 | function | Function block. |
| `memory/api/public_access_guard.py` | `_log_cloudflare_owner_access_failure` | 314-328 | function | Function block. |
| `memory/api/public_access_guard.py` | `_safe_identity_hash` | 331-335 | function | Function block. |
| `memory/api/public_access_guard.py` | `_is_cloudflare_owner_chatroom_surface` | 338-351 | function | Function block. |
| `memory/api/public_access_guard.py` | `_is_owner_session_http_surface` | 354-384 | function | Function block. |
| `memory/api/public_access_guard.py` | `_cloudflare_access_config` | 387-416 | function | Function block. |
| `memory/api/public_access_guard.py` | `_verify_cloudflare_access_jwt` | 419-431 | function | Function block. |
| `memory/api/public_access_guard.py` | `_cloudflare_jwks_client` | 434-441 | function | Function block. |
| `memory/api/public_access_guard.py` | `is_collab_public_path` | 444-490 | function | Return True for the narrow set of public guest invite/session paths. |
| `memory/api/public_access_guard.py` | `is_collab_read_request` | 493-522 | async function | Allow a validated guest to reach the READ endpoints their policy permits. |
| `memory/api/public_access_guard.py` | `is_collab_chat_write_request` | 532-553 | async function | Allow a validated guest to POST chat-class actions (message reactions). |
| `memory/api/public_access_guard.py` | `is_collab_claims_write_request` | 630-651 | async function | Allow validated full-claims collaborators to use host-level queue actions. |
| `memory/api/public_access_guard.py` | `is_collab_codebase_write_request` | 654-680 | async function | Allow validated full-codebase collaborators to use Codebase writes. |
| `memory/api/public_access_guard.py` | `is_collab_tab_write_request` | 683-709 | async function | Allow validated collaborators to use full-granted tab UI writes. |
| `memory/api/public_access_guard.py` | `_collab_read_scope_allowed` | 712-718 | async function | Async function block. |
| `memory/api/public_access_guard.py` | `_codebase_target_workspace_id` | 721-734 | function | Function block. |
| `memory/api/public_access_guard.py` | `_canonical_query_rel_path` | 737-744 | function | Function block. |
| `memory/api/public_access_guard.py` | `_collab_cookie_token` | 747-748 | function | Function block. |
| `memory/api/public_access_guard.py` | `_cookie_value` | 751-759 | function | Function block. |
| `memory/api/public_access_guard.py` | `_resolve_guest_tab_access` | 762-801 | async function | Return the tab_access for a live guest invite, or None (deny-by-default). |
| `memory/api/public_access_guard.py` | `_resolve_guest_workspace_id` | 804-809 | async function | Async function block. |
| `memory/api/public_access_guard.py` | `_guest_workspace_allowed` | 812-823 | async function | Async function block. |
| `memory/api/public_access_guard.py` | `_resolve_guest_workspace_scope` | 826-851 | async function | Async function block. |
| `memory/api/public_access_guard.py` | `_owner_token` | 854-863 | function | Function block. |
| `memory/api/public_access_guard.py` | `_owner_token_from_scope` | 866-880 | function | Function block. |
| `memory/api/public_access_guard.py` | `_headers` | 883-889 | function | Function block. |
| `memory/api/public_access_guard.py` | `_query_value` | 892-901 | function | Function block. |
| `memory/api/public_access_guard.py` | `_path_parts` | 904-905 | function | Function block. |
| `memory/api/public_access_guard.py` | `_has_allowed_static_ext` | 908-910 | function | Function block. |
| `memory/api/r2_storage.py` | `R2StorageError` | 19-20 | class | R2 operation failed without exposing credentials. |
| `memory/api/r2_storage.py` | `R2Config` | 24-28 | class | Class block. |
| `memory/api/r2_storage.py` | `_dotenv_value` | 31-43 | function | Function block. |
| `memory/api/r2_storage.py` | `_runtime_env` | 46-53 | function | Function block. |
| `memory/api/r2_storage.py` | `load_config` | 56-81 | function | Function block. |
| `memory/api/r2_storage.py` | `is_configured` | 84-89 | function | Function block. |
| `memory/api/r2_storage.py` | `put_object` | 92-121 | function | Function block. |
| `memory/api/r2_storage.py` | `delete_object` | 124-153 | function | Function block. |
| `memory/api/r2_storage.py` | `presign_get_url` | 156-184 | function | Function block. |
| `memory/api/r2_storage.py` | `_authorization_header` | 187-211 | function | Function block. |
| `memory/api/r2_storage.py` | `_signature` | 214-222 | function | Function block. |
| `memory/api/r2_storage.py` | `_canonical_request` | 225-245 | function | Function block. |
| `memory/api/r2_storage.py` | `_signing_key` | 248-252 | function | Function block. |
| `memory/api/r2_storage.py` | `_hmac` | 255-256 | function | Function block. |
| `memory/api/r2_storage.py` | `_endpoint_host` | 259-263 | function | Function block. |
| `memory/api/r2_storage.py` | `_object_url` | 266-267 | function | Function block. |
| `memory/api/r2_storage.py` | `_canonical_uri` | 270-273 | function | Function block. |
| `memory/api/r2_storage.py` | `_canonical_query` | 276-281 | function | Function block. |
| `memory/api/r2_storage.py` | `_signed_header_names` | 284-285 | function | Function block. |
| `memory/api/r2_storage.py` | `_credential_scope` | 288-289 | function | Function block. |
| `memory/api/r2_storage.py` | `_date_stamp` | 292-293 | function | Function block. |
| `memory/api/r2_storage.py` | `_amz_datetime` | 296-297 | function | Function block. |
| `memory/api/r2_storage.py` | `_content_disposition_filename` | 300-305 | function | Function block. |
| `memory/api/routes.py` | `_pms_v2_db_path` | 34-40 | function | Function block. |
| `memory/api/routes.py` | `_with_pms_v2_store` | 43-55 | function | Function block. |
| `memory/api/routes.py` | `_legacy_db_conn` | 58-69 | function | Function block. |
| `memory/api/routes.py` | `_legacy_write_pipeline` | 72-83 | function | Function block. |
| `memory/api/routes.py` | `pms_v2_retrieval_search` | 87-102 | async function | Async function block. |
| `memory/api/routes.py` | `QueryRequest` | 135-138 | class | Class block. |
| `memory/api/routes.py` | `IngestRequest` | 141-144 | class | Class block. |
| `memory/api/routes.py` | `SearchResponse` | 147-150 | class | Class block. |
| `memory/api/routes.py` | `query_memory` | 161-189 | async function | Natural language query processed by the Librarian using six-layer retrieval. |
| `memory/api/routes.py` | `ingest_content` | 195-311 | async function | Run the governance extraction chain on raw content; pending rows land in `change_log` for Marc to approve in the Actions tab. |
| `memory/api/routes.py` | `full_text_search` | 322-346 | async function | Search across all tables. |
| `memory/api/routes.py` | `read_hot_memory` | 353-375 | async function | Read the shared HOT tier content. |
| `memory/api/routes.py` | `find_stale` | 379-397 | async function | Find entries not referenced in n days. |
| `memory/api/routes.py` | `project_summary` | 401-425 | async function | Synthesized project overview. |
| `memory/api/routes.py` | `list_entries` | 431-466 | async function | List entries with optional filters. |
| `memory/api/routes.py` | `get_entry` | 470-489 | async function | Get a single entry by ID. |
| `memory/api/routes.py` | `create_entry` | 493-532 | async function | Create a new entry (goes through governance pipeline). |
| `memory/api/routes.py` | `update_entry` | 536-588 | async function | Update an existing entry (goes through governance pipeline). |
| `memory/api/routes.py` | `delete_entry` | 592-637 | async function | Delete an entry (always requires governance approval, usually escalated). |
| `memory/api/routes.py` | `_insert_record` | 648-654 | async function | Insert a new record into a table (delegates to shared operations). |
| `memory/api/routes.py` | `_update_record` | 657-661 | async function | Update fields on an existing record (delegates to shared operations). |
| `memory/api/routes.py` | `LLMGenerateRequest` | 666-669 | class | Class block. |
| `memory/api/routes.py` | `llm_generate_proxy` | 673-685 | async function | Proxy LLM calls through the API's shared Haiku subprocess. |
| `memory/api/task_routes.py` | `_normalize_agent_id` | 25-31 | function | Function block. |
| `memory/api/task_routes.py` | `_display_agent_name` | 34-38 | function | Function block. |
| `memory/api/task_routes.py` | `_normalize_task_payload` | 41-51 | function | Function block. |
| `memory/api/task_routes.py` | `ManualTaskBody` | 54-68 | class | Request body for creating a manual task suggestion. |
| `memory/api/task_routes.py` | `DelegateTaskBody` | 71-88 | class | Request body for CC-to-CC task delegation. |
| `memory/api/task_routes.py` | `TaskClaimBody` | 91-96 | class | Request body for claiming a task. |
| `memory/api/task_routes.py` | `TaskCompleteBody` | 99-104 | class | Request body for completing a task. |
| `memory/api/task_routes.py` | `_check_queue` | 107-116 | function | Guard: ensure task queue is initialized. |
| `memory/api/task_routes.py` | `_broadcast_task_event` | 119-153 | async function | Broadcast a task lifecycle event to the chatroom. |
| `memory/api/task_routes.py` | `get_pending_tasks` | 157-175 | async function | Get approved tasks waiting for pickup by an agent. |
| `memory/api/task_routes.py` | `get_suggested_tasks` | 179-186 | async function | Get tasks awaiting Executive approval. |
| `memory/api/task_routes.py` | `get_in_progress_tasks` | 190-197 | async function | Get tasks currently being worked on. |
| `memory/api/task_routes.py` | `list_tasks` | 201-220 | async function | List all tasks, optionally filtered by status. |
| `memory/api/task_routes.py` | `get_task` | 224-230 | async function | Get a single task by ID. |
| `memory/api/task_routes.py` | `create_manual_task` | 234-261 | async function | Create a manual task suggestion. |
| `memory/api/task_routes.py` | `delegate_task` | 265-294 | async function | CC-to-CC task delegation — creates task directly in approved state. |
| `memory/api/task_routes.py` | `claim_task` | 298-311 | async function | Claim an approved task (mark as in_progress). |
| `memory/api/task_routes.py` | `complete_task` | 315-330 | async function | Mark a task as completed. |
| `memory/api/task_routes.py` | `approve_task` | 334-343 | async function | Approve a suggested task via API. |
| `memory/api/task_routes.py` | `reject_task` | 347-359 | async function | Reject a suggested task via API. |
| `memory/api/task_routes.py` | `task_stats` | 363-366 | async function | Get task queue statistics. |
| `memory/api/thinker_routes.py` | `_normalize_cc_id` | 29-35 | function | Function block. |
| `memory/api/thinker_routes.py` | `_display_cc_name` | 38-42 | function | Function block. |
| `memory/api/thinker_routes.py` | `ThinkerRequest` | 45-49 | class | Request to trigger a thinker analysis pass. |
| `memory/api/thinker_routes.py` | `run_pass` | 53-77 | async function | Trigger a single Thinker analysis pass. |
| `memory/api/thinker_routes.py` | `TriageRequest` | 80-86 | class | Request to triage a specific record. |
| `memory/api/thinker_routes.py` | `triage_record` | 90-102 | async function | Triage a single record and post interesting connections to the Thinker tab. |
| `memory/api/thinker_routes.py` | `thinker_status` | 106-126 | async function | Get Thinker status and API usage. |
| `memory/api/thinker_routes.py` | `_now_iso` | 132-133 | function | Function block. |
| `memory/api/thinker_routes.py` | `_json_obj` | 136-141 | function | Function block. |
| `memory/api/thinker_routes.py` | `_canonical_payload_text` | 144-153 | function | Function block. |
| `memory/api/thinker_routes.py` | `_canonical_title` | 156-158 | function | Function block. |
| `memory/api/thinker_routes.py` | `list_canonical_ideas` | 162-213 | async function | List the Thinker fast-lane queue (thinker_intake) for the Ideas tab. |
| `memory/api/thinker_routes.py` | `IntakeVerdictRequest` | 219-221 | class | Class block. |
| `memory/api/thinker_routes.py` | `set_intake_verdict` | 225-305 | async function | Set a triage verdict on a queued intake row. |
| `memory/api/thinker_routes.py` | `dismiss_observation` | 309-332 | async function | Dismiss an item from the Ideas tab (remove it from the thinker_intake queue). |
| `memory/api/thinker_routes.py` | `clear_canonical_ideas` | 336-354 | async function | Clear the current Ideas tab queue by removing visible thinker_intake rows. |
| `memory/api/thinker_routes.py` | `ConciergeItemAction` | 360-361 | class | Class block. |
| `memory/api/thinker_routes.py` | `list_concierge_items` | 365-375 | async function | List active PMS v2 ideas and open loops for the Thoughts/Concierge tab. |
| `memory/api/thinker_routes.py` | `update_concierge_item` | 379-384 | async function | Keep or delete one Concierge-managed canonical idea/open loop. |
| `memory/api/thinker_routes.py` | `CreateSessionRequest` | 390-402 | class | Request to create a thinker session from a v2 canonical idea or freeform seed. |
| `memory/api/thinker_routes.py` | `_load_marc_profile_brief` | 405-418 | function | Load Marc's profile from memory/marc_profile.md for freeform context. |
| `memory/api/thinker_routes.py` | `create_session` | 422-455 | async function | Create a thinker session and queue it for processing. |
| `memory/api/thinker_routes.py` | `list_sessions` | 459-469 | async function | List thinker sessions, optionally filtered by status. |
| `memory/api/thinker_routes.py` | `get_session` | 473-487 | async function | Get details of a specific thinker session. |
| `memory/api/thinker_routes.py` | `update_session_category` | 491-507 | async function | Update the category of a thinker session. |
| `memory/api/thinker_routes.py` | `pause_session` | 511-520 | async function | Pause an active thinker session. |
| `memory/api/thinker_routes.py` | `resume_session` | 524-533 | async function | Resume a paused thinker session. |
| `memory/api/thinker_routes.py` | `dismiss_session` | 537-546 | async function | Dismiss a thinker session — stop resurfacing it. |
| `memory/api/thinker_routes.py` | `complete_session` | 550-559 | async function | Mark a thinker session as done. |
| `memory/api/thinker_routes.py` | `finalize_session` | 563-579 | async function | Finalize a thinker session with synthesis and PMS archival. |
| `memory/api/thinker_routes.py` | `run_reasoning_loop` | 583-604 | async function | Trigger the reasoning loop for an active session. |
| `memory/api/thinker_routes.py` | `HumanSessionMessage` | 607-610 | class | Human message in an interactive thinker session. |
| `memory/api/thinker_routes.py` | `send_session_message` | 614-664 | async function | Post a human message into a thinker session, triggering CC debate responses. |
| `memory/api/thinker_routes.py` | `_run_session_response` | 667-674 | async function | Background task: run Muse's interactive debate response. |
| `memory/api/thinker_routes.py` | `ContributeRequest` | 677-684 | class | CC contribution to a thinker session. |
| `memory/api/thinker_routes.py` | `contribute_to_session` | 688-727 | async function | Post a CC's analysis/finding to a thinker session thread. |
| `memory/api/thinker_routes.py` | `get_active_session` | 731-753 | async function | Get the currently active thinker session with recent messages. |
| `memory/api/thinker_routes.py` | `sessions_manager_status` | 757-796 | async function | Get thinker session manager status. |
| `memory/api/thinker_routes.py` | `repair_active_invariant` | 800-808 | async function | Repair stale multi-active Thinker state by requeueing empty extras. |
| `memory/api/thinker_routes.py` | `ThinkerSignalRequest` | 813-825 | class | Signal from Anvil about thinker subprocess state. |
| `memory/api/thinker_routes.py` | `receive_thinker_signal` | 829-870 | async function | Receive a thinker state signal from Anvil. |
| `memory/api/tts_routes.py` | `TTSBusyError` | 48-49 | class | Raised when realtime TTS is already busy and should drop instead of queue. |
| `memory/api/tts_routes.py` | `_xai_voice_key` | 57-61 | function | Function block. |
| `memory/api/tts_routes.py` | `_clean_for_tts` | 64-68 | function | Function block. |
| `memory/api/tts_routes.py` | `_resolve_voice` | 71-78 | function | Function block. |
| `memory/api/tts_routes.py` | `_headers` | 81-82 | function | Function block. |
| `memory/api/tts_routes.py` | `_xai_tts` | 85-107 | async function | Async function block. |
| `memory/api/tts_routes.py` | `_xai_stt` | 110-135 | async function | Async function block. |
| `memory/api/tts_routes.py` | `_acquire_tts_slot` | 141-145 | async function | Async function block. |
| `memory/api/tts_routes.py` | `_synthesize_safe` | 148-153 | async function | Async function block. |
| `memory/api/tts_routes.py` | `list_voices` | 157-159 | async function | Return xAI voice IDs in the shape the chatroom voice picker expects. |
| `memory/api/tts_routes.py` | `TTSSpeakRequest` | 162-167 | class | Class block. |
| `memory/api/tts_routes.py` | `tts_speak` | 171-195 | async function | Synthesize text via xAI and return MP3 bytes. |
| `memory/api/tts_routes.py` | `tts_stream` | 199-222 | async function | Return one NDJSON audio record. |
| `memory/api/tts_routes.py` | `tts_speak_get` | 226-233 | async function | Legacy GET endpoint for callers that still reference /api/tts. |
| `memory/api/tts_routes.py` | `KaraokeRequest` | 236-240 | class | Class block. |
| `memory/api/tts_routes.py` | `tts_karaoke` | 244-273 | async function | Synthesize sentences one at a time for karaoke reveal. |
| `memory/api/tts_routes.py` | `stt_transcribe` | 277-306 | async function | Transcribe browser-recorded audio via xAI STT. |
| `memory/api/workspace_routes.py` | `WorkspaceCreateRequest` | 24-28 | class | Class block. |
| `memory/api/workspace_routes.py` | `WorkspaceForkRequest` | 31-39 | class | Class block. |
| `memory/api/workspace_routes.py` | `WorkspacePatchRequest` | 42-47 | class | Class block. |
| `memory/api/workspace_routes.py` | `WorkspaceCodebasePatchRequest` | 50-51 | class | Class block. |
| `memory/api/workspace_routes.py` | `WorkspaceDeleteRequest` | 54-55 | class | Class block. |
| `memory/api/workspace_routes.py` | `PinnedLayoutRequest` | 58-59 | class | Class block. |
| `memory/api/workspace_routes.py` | `WorkspacePreferenceRequest` | 62-63 | class | Class block. |
| `memory/api/workspace_routes.py` | `_workspace_db_path` | 135-144 | function | Function block. |
| `memory/api/workspace_routes.py` | `_run_store` | 147-155 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_refresh_workspace_explorer_index` | 158-162 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_workspace_payload` | 165-166 | function | Function block. |
| `memory/api/workspace_routes.py` | `_normalize_repo_slug` | 169-173 | function | Function block. |
| `memory/api/workspace_routes.py` | `_validate_repo_slug` | 176-180 | function | Function block. |
| `memory/api/workspace_routes.py` | `_codebase_resolution_payload` | 183-192 | function | Function block. |
| `memory/api/workspace_routes.py` | `_decorate_workspace_payload` | 195-208 | function | Function block. |
| `memory/api/workspace_routes.py` | `_normalize_branch_path` | 211-212 | function | Function block. |
| `memory/api/workspace_routes.py` | `_workspace_tags_preference` | 215-230 | function | Function block. |
| `memory/api/workspace_routes.py` | `_workspace_branch_preference` | 233-247 | function | Function block. |
| `memory/api/workspace_routes.py` | `_set_workspace_branch_path` | 250-268 | function | Function block. |
| `memory/api/workspace_routes.py` | `_message_count` | 271-272 | function | Function block. |
| `memory/api/workspace_routes.py` | `_has_column` | 275-276 | function | Function block. |
| `memory/api/workspace_routes.py` | `_message_id_match_sql` | 279-282 | function | Function block. |
| `memory/api/workspace_routes.py` | `_message_id_match_params` | 285-288 | function | Function block. |
| `memory/api/workspace_routes.py` | `_broadcast_workspace_event` | 291-299 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_spawn_workspace_trio` | 302-308 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_reap_workspace_trio` | 311-317 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_pause_room_processes` | 320-326 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_resume_room_processes` | 329-335 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_refresh_room_agent_scope` | 338-344 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_refresh_room_agent_scopes` | 347-351 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_inherited_codebase_scope_room_ids` | 354-373 | function | Function block. |
| `memory/api/workspace_routes.py` | `_workspace_resources` | 376-400 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `list_workspaces` | 404-428 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `workspace_resources` | 432-433 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `create_workspace` | 437-476 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_create_workspace_with_branch` | 479-494 | function | Function block. |
| `memory/api/workspace_routes.py` | `fork_workspace` | 498-549 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `patch_workspace` | 553-660 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `delete_workspace` | 664-680 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `preview_fork` | 684-741 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `get_room_config` | 745-752 | async function | The two per-install permanent room ids (home + Workshop) for the browser. |
| `memory/api/workspace_routes.py` | `get_pinned_layout` | 756-760 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `put_pinned_layout` | 764-768 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `_resolve_preference_key` | 778-786 | function | Function block. |
| `memory/api/workspace_routes.py` | `get_workspace_preference` | 790-805 | async function | Generic workspace UI preference lane. |
| `memory/api/workspace_routes.py` | `put_workspace_preference` | 809-816 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `get_topology` | 820-823 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `get_active_claim_rooms` | 827-834 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `WorkspaceParentPatchRequest` | 837-838 | class | Class block. |
| `memory/api/workspace_routes.py` | `patch_workspace_parent` | 842-871 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `MemoryEdgeCreateRequest` | 874-883 | class | Class block. |
| `memory/api/workspace_routes.py` | `MemoryEdgePatchRequest` | 886-892 | class | Class block. |
| `memory/api/workspace_routes.py` | `create_memory_link` | 896-925 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `patch_memory_link` | 929-956 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `delete_memory_link` | 960-975 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `TopologyPreviewRequest` | 978-980 | class | Class block. |
| `memory/api/workspace_routes.py` | `topology_preview` | 984-1003 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `get_workspace_memory_routes` | 1007-1016 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `get_workspace_codebase` | 1020-1029 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `patch_workspace_codebase` | 1033-1075 | async function | Async function block. |
| `memory/api/workspace_routes.py` | `rebuild_workspace_memory_routes` | 1079-1101 | async function | Regenerate materialized routed views (ROLLUP_INBOX, topology debug) for a room. |
| `memory/api/workspace_routes.py` | `rebuild_all_memory_routes` | 1105-1109 | async function | Regenerate materialized routed views for every non-archived room + Main. |
| `memory/api/workspace_routes.py` | `get_workspace` | 1113-1126 | async function | Async function block. |
| `memory/chatroom/artifact_payloads.py` | `_resolve_generated_image_artifact` | 29-36 | function | Function block. |
| `memory/chatroom/artifact_payloads.py` | `_generated_image_artifact_html` | 39-40 | function | Function block. |
| `memory/chatroom/artifact_payloads.py` | `_extract_artifact_payloads` | 43-68 | function | Every persistable artifact in a message. |
| `memory/chatroom/artifact_payloads.py` | `_extract_artifact_payload` | 71-73 | function | Function block. |
| `memory/chatroom/broadcast_pipeline.py` | `_help_projection_room_id` | 45-46 | function | Function block. |
| `memory/chatroom/broadcast_pipeline.py` | `_should_broadcast_silent_marker` | 49-59 | function | True when a SILENT verdict came from an untagged chat-message wake. |
| `memory/chatroom/broadcast_pipeline.py` | `_srv` | 62-72 | function | The server module, resolved at call time. |
| `memory/chatroom/broadcast_pipeline.py` | `_project_help_message_to_floaters` | 75-111 | async function | Project HELP-room agent messages to human browsers in other rooms. |
| `memory/chatroom/broadcast_pipeline.py` | `do_broadcast` | 114-520 | async function | Actual send / persist / fanout work. |
| `memory/chatroom/broadcast_pipeline.py` | `inject_message` | 523-574 | async function | Inject a message from a non-WebSocket source (relay, API). |
| `memory/chatroom/broadcast_pipeline.py` | `broadcast_ui_only` | 577-642 | async function | Send a message to web UI connections only (not CCs). |
| `memory/chatroom/broadcast_pipeline.py` | `broadcast_topic_boundary` | 645-665 | async function | Live-render a Curator topic-boundary divider to web clients only. |
| `memory/chatroom/broadcast_pipeline.py` | `broadcast_event` | 668-694 | async function | Send a non-message event to all connections. |
| `memory/chatroom/broadcast_pipeline.py` | `broadcast_command_all_rooms` | 697-714 | async function | Broadcast a command event to every connected room. |
| `memory/chatroom/claims_orchestrator.py` | `_roster` | 34-35 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `_pick_agent` | 38-66 | function | Choose an AI to receive the dispatch. |
| `memory/chatroom/claims_orchestrator.py` | `_lease_sync` | 69-72 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `_release_sync` | 75-78 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `_next_pending_sync` | 81-86 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `enqueue_execution_dispatch_wake` | 89-105 | async function | Announce a granted lease to the assigned agent via a central wake event. |
| `memory/chatroom/claims_orchestrator.py` | `dispatch_item` | 108-134 | async function | Lease a specific pending item to exactly one agent and announce it. |
| `memory/chatroom/claims_orchestrator.py` | `dispatch_next_pending` | 137-160 | async function | Lease the next eligible pending item (Auto Follow-Up entry point). |
| `memory/chatroom/claims_orchestrator.py` | `_has_active_claim_sync` | 166-172 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `_list_pending_sync` | 175-180 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `_format_pending_board` | 183-184 | function | Function block. |
| `memory/chatroom/claims_orchestrator.py` | `ignite_deliberation` | 187-221 | async function | Auto Pick-Up re-ignite (collaborative serial autonomy). |
| `memory/chatroom/claims_orchestrator.py` | `auto_pickup_advance` | 224-234 | async function | Entry point for toggle-on and CLAIM COMPLETE under Auto Pick-Up. |
| `memory/chatroom/collab_access.py` | `normalize_tab_access` | 70-92 | function | Function block. |
| `memory/chatroom/collab_access.py` | `normalize_collab_room_id` | 95-97 | function | Function block. |
| `memory/chatroom/collab_access.py` | `normalize_collab_room_ids` | 100-127 | function | Function block. |
| `memory/chatroom/collab_access.py` | `normalize_collab_room_scope` | 130-144 | function | Function block. |
| `memory/chatroom/collab_access.py` | `collab_room_allowed` | 147-160 | function | Function block. |
| `memory/chatroom/collab_access.py` | `tab_policy_key` | 163-164 | function | Function block. |
| `memory/chatroom/collab_access.py` | `tab_access_allows` | 167-172 | function | Function block. |
| `memory/chatroom/collab_access.py` | `tab_access_options_for_ui` | 175-177 | function | Return canonical guest-grantable tab metadata for admin UI. |
| `memory/chatroom/collab_access.py` | `collab_read_policy_key` | 250-270 | function | Return the canonical tab policy key for a guest-readable GET endpoint. |
| `memory/chatroom/collab_modes.py` | `_slug` | 17-20 | function | Character-name → filesystem slug: lowercase alphanumerics joined by underscores. |
| `memory/chatroom/collab_modes.py` | `_mode_prompt_path` | 23-24 | function | Function block. |
| `memory/chatroom/collab_modes.py` | `_overlay_prompt_path` | 27-28 | function | Function block. |
| `memory/chatroom/collab_modes.py` | `_slot_for_ai_id` | 31-37 | function | Function block. |
| `memory/chatroom/collab_modes.py` | `pick_avatar_url` | 46-71 | function | Return a relative URL for a random avatar of the given persona, or None. |
| `memory/chatroom/collab_modes.py` | `_selfie_context` | 74-80 | function | Function block. |
| `memory/chatroom/collab_modes.py` | `_catalog` | 83-84 | function | Function block. |
| `memory/chatroom/collab_modes.py` | `get_mode` | 91-93 | function | Return mode definition dict or None if unknown. |
| `memory/chatroom/collab_modes.py` | `valid_mode_ids` | 96-98 | function | Return the current editable mode ids. |
| `memory/chatroom/collab_modes.py` | `normalize_mode_id` | 101-104 | function | Return mode_id if it exists in the editable catalog, otherwise default. |
| `memory/chatroom/collab_modes.py` | `get_profile` | 107-129 | function | Get the system prompt suffix for a given mode and AI slot ("ai1"/"ai2"). |
| `memory/chatroom/collab_modes.py` | `display_name_for_participant` | 132-140 | function | Resolve Muse/Anvil participant ids to the current mode character names. |
| `memory/chatroom/collab_modes.py` | `mode_list_for_ui` | 143-156 | function | Return mode list suitable for JSON response (excludes prompt text). |
| `memory/chatroom/collab_presence.py` | `remember_collab_presence` | 37-41 | function | Function block. |
| `memory/chatroom/collab_presence.py` | `forget_collab_presence` | 44-49 | function | Function block. |
| `memory/chatroom/collab_presence.py` | `collab_presence_participants` | 52-60 | function | Function block. |
| `memory/chatroom/collab_presence.py` | `debounced_collab_reset` | 63-79 | async function | Wait, then fire guest_mode_reset if no guests reconnected. |
| `memory/chatroom/collab_presence.py` | `kick_collab` | 82-130 | async function | Kick a guest by closing their WebSocket connections and revoking their token. |
| `memory/chatroom/collab_presence.py` | `log_collab_activity` | 133-159 | async function | Insert a row into guest_activity_log. |
| `memory/chatroom/collab_presence.py` | `active_collab_count` | 162-180 | function | Return the number of room-present guest participants. |
| `memory/chatroom/collab_presence.py` | `collab_presence` | 183-191 | function | Return the explicit room-scoped guest-present signal for context gates. |
| `memory/chatroom/collab_session_hub.py` | `_split_sentences` | 63-76 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_detect_end_session_token` | 97-100 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_strip_end_session_token` | 103-104 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_now_utc` | 154-155 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_now_iso` | 158-159 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_expires_iso` | 162-163 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_parse_iso` | 166-172 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_json_loads` | 175-183 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_normalize_room_id` | 186-188 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_participant_id_for_session` | 191-193 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_split_display_name` | 196-202 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_mode_display_names` | 205-208 | function | Return (ai1_name, ai2_name) for a given mode. |
| `memory/chatroom/collab_session_hub.py` | `_collab_mode_prompt` | 211-223 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_pair_to_models` | 226-228 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_cc_model_config` | 231-233 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_clean_agent_output` | 236-263 | function | Apply the shared main-room discipline to a guest-agent stdout string. |
| `memory/chatroom/collab_session_hub.py` | `_build_transcript_text` | 266-274 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `_active_claim_warning` | 277-293 | function | Return warning lines if any catchup message contains a [CLAIM:] tag from another agent. |
| `memory/chatroom/collab_session_hub.py` | `_format_reaction_summary` | 296-306 | function | Format a reactions dict into a human-readable summary, skipping the agent itself. |
| `memory/chatroom/collab_session_hub.py` | `_render_transcript_html` | 309-332 | function | Function block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess` | 335-574 | class | Class block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess.__init__` | 336-363 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess.start` | 365-408 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess.stop` | 410-438 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess.send_turn` | 440-449 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess._stdout_reader` | 451-523 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess._stderr_reader` | 525-535 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabAgentProcess._send_to_claude` | 537-574 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession` | 578-1547 | class | Class block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.start` | 645-751 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.stop` | 753-769 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.guest_connected` | 771-775 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.collab_disconnected` | 777-782 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.post_external_message` | 784-813 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._on_agent_suppressed` | 815-829 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._handle_agent_text` | 831-925 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._emit_with_floor_check` | 927-993 | async method | Run dedup + floor gate, then emit if the message should go out. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._emit_agent_message` | 995-1022 | async method | Persist + broadcast an AI message and update slot tracking state. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._compute_window_duration` | 1026-1033 | method | Floor window: off=0, on=host-set, auto=WPM-scaled (min 3s). |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._schedule_floor_timer` | 1035-1041 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._floor_timer_loop` | 1043-1048 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._close_floor_window` | 1050-1080 | async method | Drain parked drafts and fire revise-opportunity wakes. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._fire_revise_opportunity` | 1082-1120 | async method | Stash the pending-revise context and send a fresh-decision wake to the slot. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._park_draft` | 1122-1134 | async method | Park a non-holder draft during an open floor window. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._parse_mention_slot` | 1138-1156 | method | Return 'ai1'/'ai2' if text mentions that persona by name, else None. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._trigger_response` | 1158-1224 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._delta_for_slot` | 1226-1231 | method | Return messages the given slot's subprocess hasn't already seen. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._mark_seen` | 1233-1239 | method | Advance a slot's cursor past the given messages. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._trigger_peer_wake` | 1241-1295 | async method | Wake the peer AI after the lead speaks so it can react or stay silent. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._reset_idle_nudge` | 1297-1307 | method | Cancel any pending idle nudge and schedule a new one. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._idle_nudge_loop` | 1309-1394 | async method | After _IDLE_NUDGE_SECONDS of silence, nudge the non-last AI. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._build_turn_prompt` | 1396-1425 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._session_timeout_loop` | 1427-1432 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._silence_watchdog` | 1434-1467 | async method | Fire if an agent subprocess doesn't complete its turn within `timeout` seconds. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._disconnect_grace_loop` | 1469-1477 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._initial_attachments` | 1479-1487 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession._build_agent_prompt` | 1489-1515 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabRuntimeSession.handle_reaction_update` | 1517-1547 | async method | Inject a reaction notice into the next turn prompt for the slot that sent the reacted message. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub` | 1550-3161 | class | Class block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.__init__` | 1551-1571 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.start` | 1573-1575 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.stop` | 1577-1585 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._chatroom_server` | 1587-1592 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._remember_chatroom_collab_presence` | 1594-1597 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._forget_chatroom_collab_presence` | 1599-1602 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._live_chatroom_collab_connection_count` | 1604-1648 | method | Count live chatroom sockets for a collab session participant. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._collab_connection_count` | 1650-1667 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._workspace_exists` | 1669-1684 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._require_workspace` | 1686-1690 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._resolve_workspace_scope` | 1692-1712 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._room_scope_payload` | 1714-1719 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._notify_collab_policy_changed` | 1721-1734 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.create_invite` | 1736-1820 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_invite_info` | 1822-1848 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._invite_link_payload` | 1850-1861 | method | Method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.list_invite_links` | 1863-1872 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.revoke_invite_link` | 1874-1894 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.join_invite` | 1896-2030 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.approve_session` | 2032-2063 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.reject_session` | 2065-2086 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.end_session` | 2088-2118 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.mark_disconnect_deadline` | 2120-2126 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.persist_message` | 2128-2179 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_session_messages` | 2181-2198 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_session_transcript` | 2200-2244 | async method | Derive the session transcript from the live room store. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_collab_own_messages` | 2246-2301 | async method | Return only the guest's OWN messages for the session. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_session` | 2303-2329 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_session_prompts` | 2331-2338 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_collab` | 2340-2343 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_collab_notes` | 2345-2347 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_collab_memory_facts` | 2349-2355 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_collab_detail` | 2357-2375 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.list_collabs` | 2377-2382 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.get_admin_overview` | 2384-2430 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.update_collab_notes` | 2432-2447 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.send_host_message` | 2449-2453 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.set_session_pacing` | 2455-2470 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.extend_session` | 2472-2495 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.set_session_paused` | 2497-2513 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.update_session_tab_access` | 2515-2531 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.create_access_request` | 2533-2578 | async method | Record a guest's request to have a specific tab opened. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.list_session_access_requests` | 2580-2589 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.resolve_access_request` | 2591-2622 | async method | Host approves or denies a guest access request. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.send_transcript_email_now` | 2624-2631 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.connect_collab_socket` | 2633-2675 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.connect_admin_socket` | 2677-2689 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.broadcast_session_event` | 2691-2699 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.broadcast_admin_event` | 2701-2709 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.emit_prompt_debug` | 2711-2727 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub.notify_reaction_update` | 2729-2757 | async method | Forward a reaction_update to the guest session that owns this message, if any. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._collab_session_payload` | 2759-2789 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._activate_session` | 2791-2798 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._schedule_lobby_expiry` | 2800-2827 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._notify_pending_lobby` | 2829-2839 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._record_transcript_email_status` | 2841-2862 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._send_transcript_email` | 2864-2903 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._extract_collab_memory` | 2905-2953 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._upsert_collab` | 2955-2985 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._sync_legacy_profile` | 2987-3005 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._backfill_from_legacy` | 3007-3110 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._sync_existing_collabs_to_pms` | 3112-3120 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._sync_collab_to_pms` | 3122-3144 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._table_exists` | 3146-3151 | async method | Async method block. |
| `memory/chatroom/collab_session_hub.py` | `CollabSessionHub._time_remaining_seconds` | 3153-3161 | method | Method block. |
| `memory/chatroom/curator_wake.py` | `_workspace_curator_port` | 31-36 | function | Function block. |
| `memory/chatroom/curator_wake.py` | `should_wake_curator` | 39-47 | function | Function block. |
| `memory/chatroom/curator_wake.py` | `_send_curator_wake_batch` | 50-76 | async function | Async function block. |
| `memory/chatroom/curator_wake.py` | `notify_curator_message` | 79-100 | async function | Chatroom on_message callback; returns immediately after scheduling wake. |
| `memory/chatroom/daemon_lifecycle.py` | `_ps_quote_env_value` | 44-45 | function | Function block. |
| `memory/chatroom/daemon_lifecycle.py` | `MainRoomDaemonManager` | 48-214 | class | Stop/launch/targets for one main-room daemon at a time. |
| `memory/chatroom/daemon_lifecycle.py` | `MainRoomDaemonManager.__init__` | 56-71 | method | Method block. |
| `memory/chatroom/daemon_lifecycle.py` | `MainRoomDaemonManager.targets` | 73-93 | method | Method block. |
| `memory/chatroom/daemon_lifecycle.py` | `MainRoomDaemonManager.stop` | 95-122 | method | Stop one persistent main-room daemon without touching API. |
| `memory/chatroom/daemon_lifecycle.py` | `MainRoomDaemonManager.launch` | 124-214 | method | Method block. |
| `memory/chatroom/debug_stream.py` | `_env_int` | 29-33 | function | Function block. |
| `memory/chatroom/debug_stream.py` | `write_event` | 40-73 | function | Append one structured event to the debug stream. |
| `memory/chatroom/floor_control.py` | `compute_window_duration` | 29-40 | function | Return the buffer window duration in seconds for the current pacing mode. |
| `memory/chatroom/floor_control.py` | `schedule_floor_timer` | 43-51 | function | Cancel any existing floor timer and schedule a new one. |
| `memory/chatroom/floor_control.py` | `floor_timer_loop` | 54-60 | async function | Sleep for duration then close the floor window. |
| `memory/chatroom/floor_control.py` | `close_floor_window` | 63-116 | async function | Close the active floor window. |
| `memory/chatroom/floor_control.py` | `park_draft` | 119-154 | async function | Park a non-holder AI message during an open floor window. |
| `memory/chatroom/floor_control.py` | `persist_floor_parked` | 157-171 | function | Write the current parked list to disk so restarts don't lose orphaned entries. |
| `memory/chatroom/floor_control.py` | `clear_floor_parked_file` | 174-188 | function | Drop persisted parked drafts for one room, preserving any others. |
| `memory/chatroom/generated_media.py` | `workspace_generated_media_root` | 46-47 | function | Function block. |
| `memory/chatroom/generated_media.py` | `ensure_workspace_generated_media_root` | 50-53 | function | Function block. |
| `memory/chatroom/generated_media.py` | `media_mime` | 56-63 | function | Function block. |
| `memory/chatroom/generated_media.py` | `is_generated_media_path` | 66-67 | function | Function block. |
| `memory/chatroom/generated_media.py` | `resolve_workspace_media` | 70-80 | function | Function block. |
| `memory/chatroom/generated_media.py` | `resolve_codex_media` | 83-91 | function | Function block. |
| `memory/chatroom/generated_media.py` | `_safe_media_name` | 94-97 | function | Function block. |
| `memory/chatroom/generated_media.py` | `copy_media_to_workspace` | 100-115 | function | Function block. |
| `memory/chatroom/generated_media.py` | `iter_media_files` | 118-125 | function | Function block. |
| `memory/chatroom/generated_media.py` | `snapshot_media_files` | 128-129 | function | Function block. |
| `memory/chatroom/generated_media.py` | `new_media_files` | 132-134 | function | Function block. |
| `memory/chatroom/generated_media.py` | `copy_new_codex_media_to_workspace` | 137-143 | function | Function block. |
| `memory/chatroom/generated_media.py` | `snapshot_grok_media_files` | 146-147 | function | Function block. |
| `memory/chatroom/generated_media.py` | `copy_new_grok_media_to_workspace` | 150-156 | function | Function block. |
| `memory/chatroom/generated_media.py` | `generated_media_artifact_html` | 159-182 | function | Function block. |
| `memory/chatroom/guest.py` | `InviteToken` | 17-48 | class | A time-limited guest invite. |
| `memory/chatroom/guest.py` | `InviteToken.is_expired` | 34-40 | method | Check if this invite has expired. |
| `memory/chatroom/guest.py` | `InviteToken.is_valid` | 42-48 | method | Check if this invite can still be used. |
| `memory/chatroom/guest.py` | `InviteManager` | 51-201 | class | In-memory manager for guest invite tokens. |
| `memory/chatroom/guest.py` | `InviteManager.__init__` | 54-55 | method | Method block. |
| `memory/chatroom/guest.py` | `InviteManager.create_invite` | 57-94 | method | Create a new invite token. |
| `memory/chatroom/guest.py` | `InviteManager.validate_token` | 96-102 | method | Check if a token is valid for use. |
| `memory/chatroom/guest.py` | `InviteManager.consume_token` | 104-118 | method | Mark a token as used by a guest. |
| `memory/chatroom/guest.py` | `InviteManager.release_collab` | 120-125 | method | Clear active_guest_id when a guest disconnects. |
| `memory/chatroom/guest.py` | `InviteManager.revoke_token` | 127-134 | method | Revoke an invite token. |
| `memory/chatroom/guest.py` | `InviteManager.revoke_by_collab_id` | 136-149 | method | Find and revoke the invite for a connected guest. |
| `memory/chatroom/guest.py` | `InviteManager.get_collab_token` | 151-156 | method | Get the invite token associated with a guest ID. |
| `memory/chatroom/guest.py` | `InviteManager.list_invites` | 158-177 | method | Return all invites with status info. |
| `memory/chatroom/guest.py` | `InviteManager.active_collab_count` | 179-184 | method | Return the number of currently connected guests. |
| `memory/chatroom/guest.py` | `InviteManager._cleanup_expired` | 186-201 | method | Remove expired and revoked invites older than 1 hour. |
| `memory/chatroom/guest_pms_bridge.py` | `_clean` | 16-17 | function | Function block. |
| `memory/chatroom/guest_pms_bridge.py` | `_compact_dict` | 20-21 | function | Function block. |
| `memory/chatroom/guest_pms_bridge.py` | `_email_addresses` | 24-30 | function | Function block. |
| `memory/chatroom/guest_pms_bridge.py` | `_known_facts` | 33-40 | function | Function block. |
| `memory/chatroom/guest_pms_bridge.py` | `_last_session` | 43-58 | function | Function block. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge` | 61-152 | class | Mirror guest identity and memory into PMS v2 canonical storage. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge.__init__` | 64-69 | method | Method block. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge.db_path` | 72-73 | method | Method block. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge.close` | 75-77 | method | Method block. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge._existing_collab_canonical` | 79-80 | method | Method block. |
| `memory/chatroom/guest_pms_bridge.py` | `CollabPmsBridge.sync_collab_profile` | 82-152 | async method | Async method block. |
| `memory/chatroom/guide_context.py` | `_clean_token` | 15-17 | function | Function block. |
| `memory/chatroom/guide_context.py` | `_clean_label` | 20-22 | function | Function block. |
| `memory/chatroom/guide_context.py` | `normalize_guide_context` | 25-77 | function | Return the compact, prompt-safe subset of browser awareness payloads. |
| `memory/chatroom/guide_context.py` | `format_guide_context` | 80-119 | function | Format awareness context for the existing wake framing slot. |
| `memory/chatroom/help_room_intro.py` | `maybe_trigger_intro` | 31-84 | async function | Enqueue a Muse intro wake if a human just joined an empty home room. |
| `memory/chatroom/help_room_intro.py` | `maybe_gate_anvil_for_empty_intro` | 87-118 | async function | Gate Anvil early when the HELP room is still an empty intro surface. |
| `memory/chatroom/help_walkthrough_visibility.py` | `is_help_home_room` | 16-18 | function | Function block. |
| `memory/chatroom/help_walkthrough_visibility.py` | `is_help_customer_visible` | 21-40 | function | Function block. |
| `memory/chatroom/help_walkthrough_visibility.py` | `payload_help_customer_visible` | 43-53 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_srv` | 74-84 | function | The server module, resolved at call time. |
| `memory/chatroom/history_debug.py` | `synthetic_silent_marker_debug_id` | 87-94 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_model_dump` | 97-104 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_payload_ids` | 107-113 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_payload_mentions` | 116-120 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_source_message_allows_silent_marker` | 123-136 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_coerce_json_dict` | 139-148 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_silent_debug_body` | 151-157 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_silent_debug_message_id` | 160-162 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_silent_payload_marker_ids` | 165-174 | function | Function block. |
| `memory/chatroom/history_debug.py` | `_load_silent_token_debug_rows` | 177-191 | function | Function block. |
| `memory/chatroom/history_debug.py` | `augment_history_payloads_with_silent_markers` | 194-303 | function | Add transient historical silence bars from durable debug events. |
| `memory/chatroom/history_debug.py` | `census_log` | 310-333 | function | Function block. |
| `memory/chatroom/history_debug.py` | `get_history` | 336-360 | function | Return recent message history. |
| `memory/chatroom/history_debug.py` | `get_history_batch` | 363-427 | function | Return a cursor-friendly history batch for unread pulls. |
| `memory/chatroom/history_debug.py` | `_collab_receipt_history_payload` | 430-444 | function | Strip AI receipt metadata from guest-visible messages they do not own. |
| `memory/chatroom/history_debug.py` | `get_debug_log` | 447-458 | function | Return recent debug events from the ring buffer. |
| `memory/chatroom/history_debug.py` | `ensure_prompt_debug_table` | 461-510 | function | Function block. |
| `memory/chatroom/history_debug.py` | `persist_prompt_debug_event` | 513-534 | function | Function block. |
| `memory/chatroom/history_debug.py` | `get_debug_page` | 537-599 | function | Return a cursor page of durable prompt debug events, newest first. |
| `memory/chatroom/history_debug.py` | `send_history` | 602-909 | async function | Send history to a connecting client. |
| `memory/chatroom/idle_nudge.py` | `_srv` | 29-38 | function | The server module, resolved at call time. |
| `memory/chatroom/idle_nudge.py` | `arm_idle_nudge_timer` | 46-82 | function | Cancel any pending idle nudge and schedule a new one if eligible. |
| `memory/chatroom/idle_nudge.py` | `pick_idle_nudge_target` | 85-101 | function | Pick which AI to wake. |
| `memory/chatroom/idle_nudge.py` | `idle_nudge_loop` | 104-229 | async function | After _IDLE_NUDGE_SECONDS of silence, enqueue a room-local nudge. |
| `memory/chatroom/message_router.py` | `_global_agent_restart_targets` | 49-66 | async function | Async function block. |
| `memory/chatroom/message_router.py` | `_process_handle_live` | 69-76 | function | Function block. |
| `memory/chatroom/message_router.py` | `_participant_has_live_process` | 79-106 | function | Function block. |
| `memory/chatroom/message_router.py` | `_srv` | 109-119 | function | The server module, resolved at call time. |
| `memory/chatroom/message_router.py` | `_restart_agent_from_button` | 122-201 | async function | Async function block. |
| `memory/chatroom/message_router.py` | `handle_message` | 204-894 | async function | Process an incoming message from a WebSocket client. |
| `memory/chatroom/models.py` | `is_collab` | 29-31 | function | Check if a participant ID belongs to a guest. |
| `memory/chatroom/models.py` | `ChatMessage` | 34-93 | class | A single chatroom message. |
| `memory/chatroom/models.py` | `ChatMessage.extract_mentions` | 83-93 | method | Extract @mention targets from message text. |
| `memory/chatroom/models.py` | `Participant` | 96-116 | class | A connected chatroom participant. |
| `memory/chatroom/models.py` | `Workspace` | 119-137 | class | An owner-controlled chat room. |
| `memory/chatroom/models.py` | `PlanItem` | 140-170 | class | A pending Claims queue item stored in the legacy plan_items table. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier` | 21-148 | class | Posts PMS notifications into the chatroom hub. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier.__init__` | 27-28 | method | Method block. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier.notify` | 30-41 | async method | Post a plain system notification to the chatroom. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier.notify_task_suggestion` | 43-85 | async method | Post a task suggestion to the governance tab with approve/reject UI. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier.notify_thinker` | 87-101 | async method | Post a thinker finding to the Thinker tab for CC synthesis. |
| `memory/chatroom/notifier.py` | `ChatroomNotifier.notify_escalation` | 103-148 | async method | Post a governance escalation to the chatroom with approval instructions. |
| `memory/chatroom/orchestrator_v3/events.py` | `WakeEvent` | 43-80 | class | Class block. |
| `memory/chatroom/orchestrator_v3/events.py` | `WakeEvent.room_id` | 54-62 | method | Room this wake belongs to, inferred from payload/message when present. |
| `memory/chatroom/orchestrator_v3/events.py` | `WakeEvent.dedupe_key` | 64-65 | method | Method block. |
| `memory/chatroom/orchestrator_v3/events.py` | `WakeEvent.to_wire` | 67-80 | method | Outbound WebSocket payload shape (consumed by client in slice 2). |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue` | 23-108 | class | Per-room, per-target FIFO with dedupe. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.__init__` | 29-34 | method | Method block. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue._room_id` | 37-38 | method | Method block. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue._queue_key` | 40-41 | method | Method block. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.enqueue` | 43-65 | method | Try to accept an event. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.pop` | 67-75 | method | Remove and return the next event for `target` in `room_id`, or None if empty. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.peek` | 77-81 | method | Method block. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.pending` | 83-85 | method | Method block. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.mark_delivered` | 87-93 | method | Release the dedupe key for `event_id` so a future logically-distinct recurrence (e.g. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.drop` | 95-104 | method | Drop a queued event by id (e.g. |
| `memory/chatroom/orchestrator_v3/wake_queue.py` | `WakeQueue.held_keys` | 106-108 | method | Test/inspection helper -- the set of dedupe keys currently held. |
| `memory/chatroom/participant_status.py` | `_srv` | 50-61 | function | The server module, resolved at call time. |
| `memory/chatroom/participant_status.py` | `display_name_for_participant` | 64-69 | function | Function block. |
| `memory/chatroom/participant_status.py` | `runtime_label_for_participant` | 72-76 | function | Function block. |
| `memory/chatroom/participant_status.py` | `model_for_participant` | 79-87 | function | Function block. |
| `memory/chatroom/participant_status.py` | `effort_for_participant` | 90-95 | function | Function block. |
| `memory/chatroom/participant_status.py` | `service_tier_for_participant` | 98-106 | function | Function block. |
| `memory/chatroom/participant_status.py` | `runtime_metadata_for_participant` | 109-121 | function | Function block. |
| `memory/chatroom/participant_status.py` | `stamp_runtime_metadata` | 124-133 | function | Function block. |
| `memory/chatroom/participant_status.py` | `apply_mode_participant_names` | 136-157 | async function | Async function block. |
| `memory/chatroom/participant_status.py` | `participant_connected` | 160-165 | function | Function block. |
| `memory/chatroom/participant_status.py` | `update_participant_pid` | 168-195 | async function | Update a participant's PID (e.g. |
| `memory/chatroom/participant_status.py` | `update_participant_statusline` | 198-333 | async function | Update a participant's statusline fields (ctx_remaining, model_id, cc_version, cost_duration_ms). |
| `memory/chatroom/participant_status.py` | `get_participants` | 336-495 | function | Return list of participants with connection status. |
| `memory/chatroom/participant_status.py` | `send_participants` | 498-513 | async function | Send current participant list to a specific connection. |
| `memory/chatroom/participant_status.py` | `broadcast_participant_snapshot` | 516-533 | async function | Broadcast the recovered participant truth for a room. |
| `memory/chatroom/plan_store.py` | `_now_iso` | 63-64 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_expiry_iso` | 67-70 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_parse_iso` | 73-80 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_normalize_claim_label` | 83-84 | function | Function block. |
| `memory/chatroom/plan_store.py` | `claim_label_similarity` | 87-100 | function | Return a loose 0..1 similarity score for claim race deduping. |
| `memory/chatroom/plan_store.py` | `_load_list` | 103-110 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_row_to_plan_item` | 113-136 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_append_audit` | 139-151 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_audit_event_count` | 154-155 | function | Function block. |
| `memory/chatroom/plan_store.py` | `create_plan_item` | 158-199 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_find_active_duplicate` | 202-211 | function | Function block. |
| `memory/chatroom/plan_store.py` | `find_recent_similar_plan_item` | 214-255 | function | Return the newest active peer claim that fuzzily collides with `label`. |
| `memory/chatroom/plan_store.py` | `get_plan_item` | 258-261 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_supersede_duplicate_siblings` | 270-302 | function | Retire idle same-label duplicates in the room after `item_id` completes. |
| `memory/chatroom/plan_store.py` | `list_plan_items` | 305-327 | function | Function block. |
| `memory/chatroom/plan_store.py` | `lease_plan_item` | 330-382 | function | Atomically lease a PENDING item to exactly one agent. |
| `memory/chatroom/plan_store.py` | `heartbeat_plan_item` | 385-402 | function | Function block. |
| `memory/chatroom/plan_store.py` | `mark_running` | 405-428 | function | Function block. |
| `memory/chatroom/plan_store.py` | `_completion_audit_detail` | 431-463 | function | Function block. |
| `memory/chatroom/plan_store.py` | `complete_plan_item` | 466-526 | function | Function block. |
| `memory/chatroom/plan_store.py` | `reject_plan_item` | 529-543 | function | Function block. |
| `memory/chatroom/plan_store.py` | `cancel_plan_item` | 546-559 | function | Function block. |
| `memory/chatroom/plan_store.py` | `release_lease` | 562-581 | function | Force-release a leased-but-not-started item back to the pool. |
| `memory/chatroom/plan_store.py` | `mark_stale` | 584-597 | function | Function block. |
| `memory/chatroom/plan_store.py` | `reap_stale_leases` | 611-647 | function | Return any expired-lease items in `statuses` to the pool. |
| `memory/chatroom/plan_store.py` | `reap_unstarted_dispatch_leases` | 650-734 | function | Return leased-but-never-started dispatches to pending after a short grace. |
| `memory/chatroom/pms_v2_archive_bridge.py` | `build_shadow_event_client` | 20-47 | function | Create the PMS v2 shadow client without making src import layout brittle. |
| `memory/chatroom/pms_v2_archive_bridge.py` | `ChatroomPmsV2ArchiveBridge` | 50-64 | class | Mirrors durable chatroom messages into the PMS v2 append-only archive. |
| `memory/chatroom/pms_v2_archive_bridge.py` | `ChatroomPmsV2ArchiveBridge.__init__` | 53-54 | method | Method block. |
| `memory/chatroom/pms_v2_archive_bridge.py` | `ChatroomPmsV2ArchiveBridge.__call__` | 56-64 | async method | Async method block. |
| `memory/chatroom/process_identity.py` | `PidHandle` | 46-59 | class | Popen-like handle for workspace processes recovered from PID files. |
| `memory/chatroom/process_identity.py` | `PidHandle.__init__` | 49-50 | method | Method block. |
| `memory/chatroom/process_identity.py` | `PidHandle.poll` | 52-59 | method | Method block. |
| `memory/chatroom/process_identity.py` | `workspace_process_slug` | 62-63 | function | Function block. |
| `memory/chatroom/process_identity.py` | `workspace_pid_path` | 66-68 | function | Function block. |
| `memory/chatroom/process_identity.py` | `proc_matches_participant` | 71-101 | function | Confirm a chatroom_client process is THIS participant, not a sibling. |
| `memory/chatroom/process_identity.py` | `pid_belongs_to_workspace` | 104-133 | function | Verify a recovered PID actually belongs to the expected workspace agent. |
| `memory/chatroom/process_identity.py` | `process_belongs_to_workspace_process` | 136-171 | function | Verify a live process belongs to one workspace participant. |
| `memory/chatroom/process_identity.py` | `workspace_agent_port` | 174-176 | function | Function block. |
| `memory/chatroom/process_identity.py` | `curator_wake_port` | 179-186 | function | Wake port for a room's curator. |
| `memory/chatroom/process_identity.py` | `tcp_port_open` | 189-194 | function | Function block. |
| `memory/chatroom/process_identity.py` | `wait_for_curator_wake_port_closed` | 197-205 | function | Block until the room's curator wake port stops accepting connections. |
| `memory/chatroom/process_identity.py` | `curator_stats_path` | 208-212 | function | Stats file for a room's curator. |
| `memory/chatroom/reactions_feedback.py` | `_srv` | 51-60 | function | The server module, resolved at call time. |
| `memory/chatroom/reactions_feedback.py` | `_prune_legacy_reaction_events` | 63-87 | async function | Async function block. |
| `memory/chatroom/reactions_feedback.py` | `react_to_message` | 90-265 | async function | Toggle a reaction on a message. |
| `memory/chatroom/reactions_feedback.py` | `get_message_reactions` | 268-283 | async function | Return reactions for a message as {emoji: [participant_id, ...]}. |
| `memory/chatroom/reactions_feedback.py` | `get_bulk_reactions` | 286-302 | async function | Return reactions for multiple messages at once. |
| `memory/chatroom/reactions_feedback.py` | `recent_assistant_target` | 305-318 | function | Return the assistant message a human feedback message likely targets. |
| `memory/chatroom/reactions_feedback.py` | `capture_language_feedback` | 321-373 | async function | Persist clear Marc natural-language feedback on the previous assistant turn. |
| `memory/chatroom/reactions_feedback.py` | `attach_reactions_to_payloads` | 376-391 | function | Function block. |
| `memory/chatroom/reveal_gate.py` | `_clean_text` | 26-28 | function | Function block. |
| `memory/chatroom/reveal_gate.py` | `_clean_token` | 31-33 | function | Function block. |
| `memory/chatroom/reveal_gate.py` | `_clean_token_list` | 36-49 | function | Function block. |
| `memory/chatroom/reveal_gate.py` | `normalize_reveal_packet` | 52-71 | function | Return a bounded true-fact packet for a reveal wake. |
| `memory/chatroom/reveal_gate.py` | `packet_has_true_fact` | 74-75 | function | Function block. |
| `memory/chatroom/reveal_gate.py` | `format_reveal_packet` | 78-101 | function | Function block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry` | 7-88 | class | Room -> participant -> sockets mapping. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.__init__` | 15-16 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.connect` | 18-19 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.disconnect` | 21-29 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.find` | 31-32 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.iter_room` | 34-39 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.iter_all` | 41-47 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.rooms_for` | 49-54 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.room_size` | 56-57 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.participant_count` | 59-60 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.is_empty_room` | 62-63 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.as_participant_map` | 65-69 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.clear` | 71-72 | method | Method block. |
| `memory/chatroom/room_registry.py` | `RoomConnectionRegistry.drop_room` | 74-88 | method | Remove every socket in a room and return them as (participant_id, ws) pairs. |
| `memory/chatroom/runtime_labels.py` | `model_manifest` | 20-22 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `_manifest_entries` | 25-33 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `_manifest_entry_for` | 36-41 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `manifest_select_values` | 44-49 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `manifest_dropdown_options` | 52-65 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `normalize_claude_model_id` | 73-77 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `resolved_model_id_for_display` | 80-85 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `harness_for_model` | 88-98 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `supports_fast_mode` | 101-107 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `normalize_effort_for_model` | 110-117 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `supported_efforts_for_model` | 120-128 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `model_display_label` | 131-157 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `effort_display_label` | 160-163 | function | Function block. |
| `memory/chatroom/runtime_labels.py` | `runtime_display_label` | 166-171 | function | Function block. |
| `memory/chatroom/server.py` | `_workspace_codebase_scope_env` | 152-170 | function | Function block. |
| `memory/chatroom/server.py` | `_active_backend_provider` | 227-229 | function | Function block. |
| `memory/chatroom/server.py` | `_build_default_agent_config` | 232-237 | function | Function block. |
| `memory/chatroom/server.py` | `_model_select_value` | 250-262 | function | Function block. |
| `memory/chatroom/server.py` | `_default_agent_config` | 265-266 | function | Function block. |
| `memory/chatroom/server.py` | `_agent_config_with_defaults` | 269-281 | function | Function block. |
| `memory/chatroom/server.py` | `_read_int_file` | 313-318 | function | Function block. |
| `memory/chatroom/server.py` | `_read_json_file` | 321-326 | function | Function block. |
| `memory/chatroom/server.py` | `_is_pms_v2_ingest_activity` | 329-334 | function | Function block. |
| `memory/chatroom/server.py` | `_write_pms_v2_ingest_activity_heartbeat` | 337-350 | function | Function block. |
| `memory/chatroom/server.py` | `_history_to_lines` | 353-368 | function | Return the most recent messages that fit within `limit` rendered lines. |
| `memory/chatroom/server.py` | `ChatroomServer` | 373-3487 | class | Manages WebSocket connections, message broadcast, and history. |
| `memory/chatroom/server.py` | `ChatroomServer._display_name_for_participant` | 390-391 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._runtime_label_for_participant` | 393-394 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._model_for_participant` | 396-397 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._effort_for_participant` | 399-400 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._service_tier_for_participant` | 402-403 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._runtime_metadata_for_participant` | 405-408 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._stamp_runtime_metadata` | 410-411 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._drk_event_text` | 413-425 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._apply_mode_participant_names` | 427-428 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.__init__` | 430-593 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._connections` | 596-598 | method | Backward-compatible main-room connection view during room migration. |
| `memory/chatroom/server.py` | `ChatroomServer._connections` | 601-609 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._normalize_room_id` | 612-613 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._room_participant_state` | 615-619 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.update_guide_context` | 621-625 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.guide_context_block` | 627-629 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._reveal_key` | 631-635 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._is_reveal_gated` | 637-639 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._is_help_walkthrough_active` | 641-643 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.set_reveal_gate` | 645-659 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.update_reveal_packet` | 661-675 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.reveal_packet_block` | 677-680 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.reveal_agent` | 682-725 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._ensure_room_agent_config_defaults` | 727-734 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._agent_configs_for_room` | 736-741 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._agent_config_for_participant` | 743-749 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._effective_agent_config_for_participant` | 751-769 | method | Return the config the UI should display for a participant. |
| `memory/chatroom/server.py` | `ChatroomServer._effective_agent_configs_for_room` | 771-776 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._set_agent_config` | 778-787 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._normalized_agent_config_values` | 789-822 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._normalized_agent_config_snapshot` | 824-833 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._agent_config_bulk_room_ids` | 835-852 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_unconfigured_agents` | 854-857 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_parked_for_room` | 859-860 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_broadcast_at` | 863-864 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_broadcast_at` | 867-868 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_human_msg_at` | 871-872 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_human_msg_at` | 875-876 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._idle_nudge_task` | 879-880 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._idle_nudge_task` | 883-887 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_ai_speaker` | 890-891 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._last_ai_speaker` | 894-895 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_holder_id` | 898-899 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_holder_id` | 902-903 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_window_end` | 906-907 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_window_end` | 910-911 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_window_task` | 914-915 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_window_task` | 918-922 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_parked` | 925-926 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_parked` | 929-930 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._room_id_for_ws` | 932-933 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._participant_sockets` | 935-940 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._is_muted` | 942-950 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._set_muted` | 952-956 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._participant_connected` | 958-963 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._remember_guest_presence` | 968-969 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._forget_collab_presence` | 971-972 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._collab_presence_participants` | 974-975 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._notify_collab_admin_presence_changed` | 977-985 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._normalize_connect_event` | 987-991 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._room_identity_payload` | 993-1011 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._pending_connect_event` | 1013-1015 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._read_restart_marker_data` | 1017-1031 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._claim_restart_marker_event` | 1033-1066 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._current_restart_marker_event` | 1068-1084 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._connect_status_text` | 1086-1123 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._write_agent_control_notice` | 1125-1155 | method | Persist a one-shot notice for the target agent's next wake. |
| `memory/chatroom/server.py` | `ChatroomServer.write_hard_refresh_notices` | 1157-1168 | method | Persist a one-shot hard-refresh notice for the room agents. |
| `memory/chatroom/server.py` | `ChatroomServer._write_agent_fresh_restart_flag` | 1170-1191 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.start` | 1193-1325 | async method | Start the chatroom server. |
| `memory/chatroom/server.py` | `ChatroomServer.stop` | 1327-1361 | async method | Stop the chatroom server and close all connections. |
| `memory/chatroom/server.py` | `ChatroomServer._prune_doc_status_fallback` | 1363-1383 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.on_message` | 1385-1389 | method | Register a callback for incoming messages. |
| `memory/chatroom/server.py` | `ChatroomServer._run_background` | 1391-1403 | method | Run non-critical persistence work without blocking room delivery. |
| `memory/chatroom/server.py` | `ChatroomServer._has_job_complete_line` | 1406-1408 | method | True when a message contains JOB COMPLETE exactly on its own line. |
| `memory/chatroom/server.py` | `ChatroomServer._claim_complete_label_for_toast` | 1411-1417 | method | Return the standalone [CLAIM COMPLETE: ...] label for toast alerts. |
| `memory/chatroom/server.py` | `ChatroomServer._should_notify_job_complete` | 1419-1425 | method | Return True for live chat messages that should trigger desktop/push alerts. |
| `memory/chatroom/server.py` | `ChatroomServer._should_notify_claim_complete` | 1427-1433 | method | Return True for standalone claim-complete lines that should alert Marc. |
| `memory/chatroom/server.py` | `ChatroomServer._notify_job_complete` | 1435-1439 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._notify_claim_complete` | 1441-1446 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._send_windows_toast` | 1448-1489 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._enqueue_chatroom_embedding` | 1491-1508 | method | Queue the raw chatroom row for embedding without blocking broadcast. |
| `memory/chatroom/server.py` | `ChatroomServer.connect` | 1513-1882 | async method | Register a new WebSocket connection. |
| `memory/chatroom/server.py` | `ChatroomServer._maybe_trigger_help_intro` | 1884-1894 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._maybe_gate_anvil_for_empty_help_intro` | 1896-1908 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.mark_disconnect_intent` | 1910-1919 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.disconnect` | 1921-1981 | async method | Remove a WebSocket connection. |
| `memory/chatroom/server.py` | `ChatroomServer._debounced_collab_reset` | 1983-1986 | async method | Wait, then fire guest_mode_reset if no guests reconnected. |
| `memory/chatroom/server.py` | `ChatroomServer.kick_collab` | 1988-1991 | async method | Kick a guest by closing their WebSocket connections and revoking their token. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_sync_db_path` | 1996-1999 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_to_payload` | 2002-2003 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_pid_path` | 2015-2016 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_processes` | 2019-2021 | method | Tracked workspace launcher handles; owned by WorkspaceProcessManager. |
| `memory/chatroom/server.py` | `ChatroomServer._prepare_room_agent_config` | 2023-2025 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_participant_processes` | 2027-2034 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_live_pid_handles` | 2036-2037 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._is_paused` | 2039-2041 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._set_paused` | 2043-2051 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._curator_wake_port` | 2055-2056 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._wait_for_curator_wake_port_closed` | 2058-2061 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._curator_stats_path` | 2063-2064 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._wait_for_curator_runtime_config` | 2066-2088 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._main_codebase_env` | 2092-2093 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_codebase_env` | 2095-2096 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_agent_env` | 2098-2133 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.spawn_workspace_trio` | 2138-2139 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._drop_workspace_sockets` | 2141-2161 | async method | Remove every WS in a workspace room from the registry, best-effort close. |
| `memory/chatroom/server.py` | `ChatroomServer.reap_workspace_trio` | 2163-2164 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.workspace_resource_snapshot` | 2166-2167 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.restore_active_workspace_trios` | 2169-2199 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.enforce_paused_main_room_processes` | 2201-2207 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._run_workspace_store` | 2209-2217 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._workspace_history_payloads` | 2224-2227 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._broadcast_workspace_event` | 2229-2233 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._handle_workspace_action` | 2235-2242 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.handle_message` | 2244-2252 | async method | Process an incoming message from a WebSocket client. |
| `memory/chatroom/server.py` | `ChatroomServer.broadcast_message` | 2264-2369 | async method | Dispatch entry point — all messages broadcast instantly. |
| `memory/chatroom/server.py` | `ChatroomServer._dispatch_ai_message` | 2371-2450 | async method | AI broadcast path, called with per-sender lock held. |
| `memory/chatroom/server.py` | `ChatroomServer._delayed_ws_send` | 2454-2484 | async method | Fire-and-forget WS send after a delay. |
| `memory/chatroom/server.py` | `ChatroomServer._pick_untagged_lead` | 2489-2490 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._tagged_wake_targets` | 2492-2493 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._record_claim_broadcast` | 2499-2500 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._track_claim_lifecycle` | 2502-2503 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._maybe_block_competing_claim` | 2505-2506 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._maybe_enqueue_claim_notice` | 2508-2509 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._enqueue_tagged_wake_events` | 2511-2516 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._enqueue_untagged_human_wake_events` | 2518-2524 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._enqueue_untagged_ai_peer_wake` | 2526-2531 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._arm_idle_nudge_timer` | 2536-2537 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._idle_nudge_loop` | 2539-2540 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._do_broadcast` | 2542-2545 | async method | Send / persist / fanout, delegated to broadcast_pipeline.py. |
| `memory/chatroom/server.py` | `ChatroomServer._is_collab_sender` | 2547-2550 | method | Check if a sender id is an active guest. |
| `memory/chatroom/server.py` | `ChatroomServer._compute_window_duration` | 2556-2557 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._schedule_floor_timer` | 2559-2560 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._floor_timer_loop` | 2562-2563 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._close_floor_window` | 2565-2566 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._park_draft` | 2568-2569 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer._send_event_to` | 2571-2586 | async method | Send a WS event to a single participant's connections only. |
| `memory/chatroom/server.py` | `ChatroomServer.enqueue_wake_event` | 2588-2618 | async method | Queue and opportunistically deliver a central V3 wake event. |
| `memory/chatroom/server.py` | `ChatroomServer._dispatch_next_wake_event` | 2620-2692 | async method | Send one queued wake_event frame to the target participant only. |
| `memory/chatroom/server.py` | `ChatroomServer._publish_wake_debug` | 2694-2726 | method | Mirror delivered wake routing into the Debug pane, not Activity. |
| `memory/chatroom/server.py` | `ChatroomServer._persist_floor_parked` | 2732-2733 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._clear_floor_parked_file` | 2735-2736 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.broadcast_drk_event` | 2738-2806 | async method | Broadcast a drk_event to web UI connections only (not CCs, not guests). |
| `memory/chatroom/server.py` | `ChatroomServer.inject_message` | 2808-2839 | async method | Inject a message from a non-WebSocket source (relay, API). |
| `memory/chatroom/server.py` | `ChatroomServer.react_to_message` | 2848-2852 | async method | Toggle a reaction on a message. |
| `memory/chatroom/server.py` | `ChatroomServer.get_message_reactions` | 2854-2856 | async method | Return reactions for a message as {emoji: [participant_id, ...]}. |
| `memory/chatroom/server.py` | `ChatroomServer.get_bulk_reactions` | 2858-2860 | async method | Return reactions for multiple messages at once. |
| `memory/chatroom/server.py` | `ChatroomServer._recent_assistant_target` | 2862-2864 | method | Return the assistant message a human feedback message likely targets. |
| `memory/chatroom/server.py` | `ChatroomServer._capture_language_feedback` | 2866-2868 | async method | Persist clear Marc natural-language feedback on the previous assistant turn. |
| `memory/chatroom/server.py` | `ChatroomServer.update_participant_pid` | 2874-2881 | async method | Update a participant's PID (e.g. |
| `memory/chatroom/server.py` | `ChatroomServer.update_participant_statusline` | 2883-2887 | async method | Update a participant's statusline fields (ctx_remaining, model_id, cc_version, cost_duration_ms). |
| `memory/chatroom/server.py` | `ChatroomServer._persist_server_state` | 2893-2907 | method | Write current effort / agent_config to disk. |
| `memory/chatroom/server.py` | `ChatroomServer._restore_server_state` | 2909-2948 | method | Restore effort from disk on startup. |
| `memory/chatroom/server.py` | `ChatroomServer.send_command` | 2953-2974 | async method | Send a control command to a specific participant over WebSocket. |
| `memory/chatroom/server.py` | `ChatroomServer.get_participants` | 2979-2982 | method | Return list of participants with connection status. |
| `memory/chatroom/server.py` | `ChatroomServer._attach_reactions_to_payloads` | 2984-2985 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.get_history` | 2987-2989 | method | Return recent message history. |
| `memory/chatroom/server.py` | `ChatroomServer.get_history_batch` | 2991-3001 | method | Return a cursor-friendly history batch for unread pulls. |
| `memory/chatroom/server.py` | `ChatroomServer.connected_count` | 3004-3006 | method | Number of participants with active connections. |
| `memory/chatroom/server.py` | `ChatroomServer.message_count` | 3009-3011 | method | Total messages in history buffer. |
| `memory/chatroom/server.py` | `ChatroomServer.get_debug_log` | 3013-3016 | method | Return recent debug events from the ring buffer. |
| `memory/chatroom/server.py` | `ChatroomServer._ensure_prompt_debug_table` | 3018-3019 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._persist_prompt_debug_event` | 3021-3022 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.get_debug_page` | 3024-3041 | method | Return a cursor page of durable prompt debug events, newest first. |
| `memory/chatroom/server.py` | `ChatroomServer._log_collab_activity` | 3046-3057 | async method | Insert a row into guest_activity_log. |
| `memory/chatroom/server.py` | `ChatroomServer._send_history` | 3062-3077 | async method | Send history to a connecting client (CC 50-cap, web UI DB fallback, guest filtering). |
| `memory/chatroom/server.py` | `ChatroomServer._broadcast_ui_only` | 3079-3080 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.broadcast_topic_boundary` | 3082-3105 | async method | Live-render a persisted Curator topic boundary to room web clients. |
| `memory/chatroom/server.py` | `ChatroomServer._broadcast_event` | 3107-3113 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.broadcast_command_all_rooms` | 3115-3120 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.broadcast_command` | 3122-3132 | async method | Broadcast a command event to all non-guest participants (CC orchestrators). |
| `memory/chatroom/server.py` | `ChatroomServer.send_command_to_agent` | 3134-3157 | async method | Send a command event to a single agent by participant_id. |
| `memory/chatroom/server.py` | `ChatroomServer._spawn_workspace_participant` | 3159-3161 | method | Spawn one workspace-local participant without touching sibling rooms. |
| `memory/chatroom/server.py` | `ChatroomServer._stop_workspace_participant` | 3163-3167 | method | Stop exactly one participant process in one workspace room and verify it is gone. |
| `memory/chatroom/server.py` | `ChatroomServer.restart_participant` | 3175-3179 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.pause_participant` | 3181-3190 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer.resume_participant` | 3192-3199 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._pause_participant_process` | 3201-3205 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._resume_participant_process` | 3207-3216 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._restart_workspace_participant` | 3218-3250 | method | Restart exactly one participant process in one workspace room. |
| `memory/chatroom/server.py` | `ChatroomServer._persistent_daemon_config` | 3252-3267 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._stop_persistent_daemon` | 3269-3271 | method | Stop one persistent main-room daemon without touching API. |
| `memory/chatroom/server.py` | `ChatroomServer._launch_persistent_daemon` | 3273-3274 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._restart_persistent_daemon` | 3276-3295 | method | Restart one persistent main-room daemon without touching API. |
| `memory/chatroom/server.py` | `ChatroomServer._stop_main_room_processes_sync` | 3297-3301 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._resume_main_room_processes_sync` | 3303-3309 | method | Method block. |
| `memory/chatroom/server.py` | `ChatroomServer._drop_main_agent_sockets` | 3311-3318 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.pause_room_processes` | 3325-3334 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.resume_room_processes` | 3336-3343 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.refresh_room_agent_scope` | 3345-3395 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.pause_main_room_processes` | 3397-3415 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.resume_main_room_processes` | 3417-3437 | async method | Async method block. |
| `memory/chatroom/server.py` | `ChatroomServer.active_collab_count` | 3439-3442 | method | Return the number of room-present guest participants. |
| `memory/chatroom/server.py` | `ChatroomServer.collab_presence` | 3444-3447 | method | Return the explicit room-scoped guest-present signal for context gates. |
| `memory/chatroom/server.py` | `ChatroomServer._send_participants` | 3449-3451 | async method | Send current participant list to a specific connection. |
| `memory/chatroom/server.py` | `ChatroomServer._broadcast_participant_snapshot` | 3453-3456 | async method | Broadcast the recovered participant truth for a room. |
| `memory/chatroom/server.py` | `ChatroomServer._schedule_participant_snapshot_refresh` | 3463-3487 | method | Method block. |
| `memory/chatroom/server_paths.py` | `_write_json_atomic` | 44-54 | function | Function block. |
| `memory/chatroom/server_paths.py` | `_agent_session_state_slug` | 57-60 | function | Function block. |
| `memory/chatroom/server_state.py` | `ServerStateStore` | 18-40 | class | Reads and writes the server-state JSON file under a lock. |
| `memory/chatroom/server_state.py` | `ServerStateStore.__init__` | 26-28 | method | Method block. |
| `memory/chatroom/server_state.py` | `ServerStateStore.persist` | 30-32 | method | Method block. |
| `memory/chatroom/server_state.py` | `ServerStateStore.restore` | 34-40 | method | Method block. |
| `memory/chatroom/static/backgrounds/README.md` | `Mode Background Images` | 1-15 | h1 | Markdown section: Mode Background Images. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRepoUrl` | 18-31 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateGuestUrl` | 32-47 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateWorkspaceIdForUrl` | 48-58 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRepoSlug` | 59-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateCurrentRoomId` | 63-70 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadRoomRepoBinding` | 71-84 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadRepoRegistry` | 85-105 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePopulateRepoSelect` | 106-207 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSetFileEditButtons` | 208-226 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEscapeHtml` | 227-230 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEscapeAttr` | 231-234 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessRepoKey` | 235-238 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessStorageKey` | 239-242 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessServerKey` | 243-246 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessCleanList` | 247-261 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessNormalizeState` | 262-268 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessReadLocal` | 269-278 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessSave` | 279-287 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessLoad` | 288-309 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessEnsureLoaded` | 310-314 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessBasename` | 315-319 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessDirname` | 320-326 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessIsPinned` | 327-332 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessPin` | 333-343 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessUnpin` | 344-353 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessRecordOpen` | 354-366 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessOpen` | 367-376 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessRenderList` | 377-425 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateQuickAccessRender` | 426-442 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateUpdatePinButton` | 443-461 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderLines` | 462-494 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePrismLang` | 495-506 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSplitHighlightedLines` | 507-558 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderLinesHighlighted` | 559-581 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateApplyHighlight` | 582-618 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePrismHighlightBlock` | 619-655 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateDestroyMinimap` | 656-666 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMinimapLineSpans` | 667-672 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEnsureMinimap` | 673-691 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `jumpFromEvent` | 692-724 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateScrollMinimapRatio` | 725-734 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMinimapMetrics` | 735-752 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateVisibleLineSpan` | 753-776 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMinimapLineCenterRatio` | 777-783 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateDrawMinimap` | 784-828 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateUpdateMinimapViewport` | 829-849 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateUpdateMinimapSelectionMarks` | 850-872 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRefreshMinimap` | 873-883 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateUpdateSelectionMatches` | 884-899 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEnglishHtml` | 900-920 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateIsGenericTreeSummary` | 921-927 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateGapHtml` | 928-939 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateApplyDensityMode` | 940-953 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateHydrateVisibleHistoryMode` | 954-964 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadDensityPreference` | 965-991 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateApplyWrap` | 992-1008 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadWrapPreference` | 1009-1023 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadAuthorRegistry` | 1024-1076 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSearchCodebase` | 1077-1105 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderSearchResults` | 1106-1184 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateFileIcon` | 1185-1191 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderEntries` | 1192-1305 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMdMode` | 1306-1308 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMdSetMode` | 1309-1313 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateGranularity` | 1314-1316 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSetGranularity` | 1317-1342 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateNormalizeTreePath` | 1343-1355 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateTreeItemForPath` | 1356-1364 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateTreeChildrenForDir` | 1365-1371 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateScrollChildIntoContainer` | 1372-1386 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadTreeChildren` | 1387-1409 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRevealPathInTree` | 1410-1471 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRestoreRevealedPath` | 1472-1483 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateOpenInFilesPanel` | 1484-1499 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSyncFilesPanelForOpen` | 1500-1505 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateJumpToLineAfterRender` | 1506-1540 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMdStopPoll` | 1541-1548 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateOpenMarkdownFile` | 1549-1595 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderMarkdown` | 1596-1637 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateOpenFile` | 1638-1837 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `syncGutter` | 1838-1861 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateCurrentTopVisibleLine` | 1862-1947 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateSaveGuardText` | 1948-2001 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateShowSaveGuard` | 2002-2082 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateParseDiffChangedRanges` | 2083-2088 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `flushDeletionAnchor` | 2089-2124 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRangesTouch` | 2125-2128 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateAuthorClass` | 2129-2137 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateAuthorMeta` | 2138-2146 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateHistoryStatsHtml` | 2147-2156 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderHistoryDiff` | 2157-2180 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateHistoryHtmlLegacy` | 2181-2192 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateHistoryHtml` | 2193-2215 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEventKey` | 2216-2219 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMergeRanges` | 2220-2238 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderedLineIndex` | 2239-2253 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLineForRange` | 2254-2264 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateInsertLineHistoryMarker` | 2265-2291 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateMergeHistoryEvents` | 2292-2303 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateHydrateDiffBodies` | 2304-2322 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRangesForEvent` | 2323-2338 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderHistoryPager` | 2339-2357 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderDiffHistoryEvents` | 2358-2390 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateShowDiffHistoryError` | 2391-2403 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadDiffHistory` | 2404-2462 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRecordResizeDebug` | 2463-2492 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateResizeDebugNumber` | 2493-2498 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateShowResizeDebug` | 2499-2549 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_finishDrag` | 2550-2579 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_recordButtonsZero` | 2580-2585 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_treeWidthInfo` | 2586-2594 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_applyTreeMove` | 2595-2602 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMove` | 2603-2610 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMouseMove` | 2611-2617 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onPointerUp` | 2618 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onPointerCancel` | 2619 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMouseUp` | 2620 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onBlur` | 2621 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onLostPointerCapture` | 2622-2672 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_cssHeight` | 2673-2676 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_maxSearchResultsHeight` | 2677-2690 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_clampSearchResultsHeight` | 2691-2699 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_setSearchResultsHeight` | 2700-2709 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_currentSearchResultsHeight` | 2710-2722 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_visualScaleY` | 2723-2730 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_searchHeightInfo` | 2731-2760 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_endDrag` | 2761-2788 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_recordButtonsZero` | 2789-2794 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_applySearchMove` | 2795-2803 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMove` | 2804-2811 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMouseMove` | 2812-2818 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onPointerUp` | 2819 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onPointerCancel` | 2820 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onMouseUp` | 2821 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onBlur` | 2822 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_onLostPointerCapture` | 2823-2930 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateDeeperLineByLine` | 2931-2983 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateStartEdit` | 2984-3073 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateCancelEdit` | 3074-3078 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateShowDiff` | 3079-3144 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateEscHtml` | 3145-3200 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateFetchDefinition` | 3201-3225 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderDefinition` | 3226-3262 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateUriToRelPath` | 3263-3279 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderDeps` | 3280-3319 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateCaretFromPoint` | 3320-3331 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateDepsClickHandler` | 3332-3413 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateInitGranularitySelect` | 3414-3418 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateLoadPresets` | 3419-3451 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateRenderPresetOptions` | 3452-3467 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePresetChange` | 3468-3494 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePresetOpenNew` | 3495-3508 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePresetCloseNew` | 3509-3513 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotatePresetSaveNew` | 3514-3522 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `showErr` | 3523-3563 | code | Code block. |
| `memory/chatroom/static/js/chatroom.annotate.js` | `_annotateJumpDebugLog` | 3564-3633 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_getCollabColor` | 25-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityUserName` | 44-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityUserId` | 47-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityUserLegacySenderIds` | 50-57 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityUserMentionAliases` | 58-63 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityGovernanceOwnerId` | 64-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityGovernanceCuratorId` | 67-69 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityCollabHostName` | 70-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityUserCodeAuthorId` | 73-75 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityIsUserSender` | 76-79 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityAgentName` | 80-96 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `identityParticipantName` | 97-103 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `applyRuntimeIdentity` | 104-120 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `loadRuntimeIdentity` | 121-130 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `updateStaticIdentityLabels` | 131-203 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setWs` | 204-209 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setConnected` | 210-215 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setAutoScroll` | 216-228 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setActiveTab` | 229-234 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setGovUnread` | 235-240 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setPromptsUnread` | 241-247 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setThinkerUnread` | 248-253 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setIdeasUnread` | 254-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setArtifactsUnread` | 261-321 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `collabPolicyKeyForTab` | 322-360 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `normalizeCollabTabAccess` | 361-371 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `collabCanAccessTab` | 372-379 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `setCollabPaused` | 380-392 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `applyCollabTabPolicy` | 393-477 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `openCollabAccessRequest` | 478-511 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `closer` | 512-521 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `updateCollabTabBadge` | 522-543 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_setActiveSessionId` | 544-566 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_pidName` | 567 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `_formatTime` | 568-575 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `myParticipantId` | 576-587 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `appendToTab` | 588-645 | code | Code block. |
| `memory/chatroom/static/js/chatroom.core.js` | `initChatroom` | 646-677 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbEl` | 23-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchWorkbench` | 25-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSetDrawerOpen` | 29-32 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSetActiveTabChrome` | 33-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchEscape` | 37-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchFormatBytes` | 47-54 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchFormatCount` | 55-59 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchStatus` | 60-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSetPagerVisible` | 67-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCurrentDb` | 72-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSelectedTable` | 77-80 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCurrentTableInfo` | 81-87 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchViewKey` | 88-91 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchColumnPrefsKey` | 92-95 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchGetVisibleSet` | 96-110 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSaveVisibleColumns` | 111-124 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCheckedValues` | 125-131 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCurrentVisibleColumns` | 132-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCurrentSearchColumns` | 142-145 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchActiveTextColumns` | 146-149 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchFilterParams` | 150-163 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchPopulateDatabases` | 164-176 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchLoadSavedViews` | 177-186 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchWriteSavedViews` | 187-193 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderSavedViews` | 194-207 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCurrentViewPayload` | 208-222 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSetInputValue` | 223-227 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSetChecked` | 228-232 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSaveView` | 233-248 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchLoadSelectedView` | 249-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchDeleteSelectedView` | 261-270 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchApplySavedView` | 271-311 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchVisibleTables` | 312-320 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchPopulateTables` | 321-342 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderTableList` | 343-374 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchLoadSchema` | 375-398 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRefreshCompactStats` | 399-413 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSelectTable` | 414-428 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderSchema` | 429-467 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderColumnPanel` | 468-507 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchApplyColumnVisibility` | 508-517 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchColumnPreset` | 518-547 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSearchColumnPreset` | 548-553 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchToggleIsolate` | 554-561 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCellValue` | 562-574 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchDisplayValue` | 575-589 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchOrderColumns` | 590-592 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `rank` | 593-606 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchColWidthsKey` | 607-610 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchLoadColWidths` | 611-617 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSaveColWidth` | 618-631 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchAutoWidth` | 632-650 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchAttachColResizers` | 651-656 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `setWidth` | 657-684 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `onMove` | 685-688 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `onUp` | 689-701 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderGrid` | 702-741 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchUpdatePager` | 742-761 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderBrowse` | 762-770 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchBrowseTable` | 771-816 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchBrowseSelected` | 817-822 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchResetFilters` | 823-834 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRenderSearch` | 835-843 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchRun` | 844-881 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchSortBy` | 882-892 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchPrevPage` | 893-897 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchNextPage` | 898-901 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchToggleSql` | 902-912 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSqlRun` | 913-942 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchOpenRow` | 943-975 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCloseDrawer` | 976-982 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchLoadRelated` | 983-1021 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchCopySelectedRow` | 1022-1028 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchExport` | 1029-1045 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `csvEscape` | 1046-1069 | code | Code block. |
| `memory/chatroom/static/js/chatroom.db.js` | `dbSearchWireControls` | 1070-1191 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `_identityAgentName` | 27-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `_identityUserName` | 29-264 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `load` | 265-275 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `save` | 276-280 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `reset` | 281-290 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `loadCustomThemes` | 291-302 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `saveCustomThemes` | 303-307 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `_hydrateFromServer` | 308-327 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `themeSnapshot` | 328-335 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `applyThemeValues` | 336-347 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `isValidHex` | 348-349 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `isValidUrl` | 350-356 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `escCssUrl` | 357-358 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `hexToRgba` | 359-370 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `isValidBorder` | 371-380 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `setOrClear` | 381-385 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `apply` | 386-445 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `el` | 446-459 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildColorOrBlank` | 460-468 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `commitVal` | 469-498 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildColorRgba` | 499-509 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `commitFromInputs` | 510-547 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildRangePx` | 548-583 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildRangeDecimal` | 584-622 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildSelect` | 623-638 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildBorderShorthand` | 639-659 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildControl` | 660-671 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildThemePresetsSection` | 672-676 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `addPresetButton` | 677-717 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `renderCustomThemes` | 718-729 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `addPresetButtonTo` | 730-781 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildPanel` | 782-787 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `setStatus` | 788-800 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `addSection` | 801-895 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `activateSection` | 896-923 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `_initDrawerResize` | 924-933 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `onMove` | 934-941 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `onUp` | 942-955 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `onDown` | 956-970 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildAvatarsSection` | 971-1037 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildBackgroundSection` | 1038-1076 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `syncRows` | 1077-1162 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildFontSection` | 1163-1180 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `buildGpuSection` | 1181-1214 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `openPanel` | 1215-1225 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `closePanel` | 1226-1236 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `bindHeader` | 1237-1251 | code | Code block. |
| `memory/chatroom/static/js/chatroom.settings.js` | `init` | 1252-1263 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `paneTabId` | 18-22 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `setFullscreenMode` | 23-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `resetAllFullscreenButtons` | 28-35 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `exitFullscreen` | 36-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `setFullscreenForPane` | 44-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `toggleFullscreen` | 61-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `openInNewTab` | 67-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `openTabUrl` | 73-85 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `paneKeyFor` | 86-90 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `openPaneUrl` | 91-101 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `panelTabKey` | 102-106 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `clearPanelFullscreen` | 107-117 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `setFullscreenForPanelPane` | 118-135 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `togglePanelFullscreen` | 136-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `injectToolbar` | 142-173 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `removeTabRowTopicsButton` | 174-180 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `injectPanelPaneControls` | 181-221 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `_safe` | 222-225 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `injectAll` | 226-234 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `_observePanelStacks` | 235-254 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `applyBootParams` | 255-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `applyPane` | 261-292 | code | Code block. |
| `memory/chatroom/static/js/chatroom.tabchrome.js` | `init` | 293-310 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_el` | 59-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_escapeHtml` | 61-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_escapeAttr` | 67-70 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_getJson` | 71-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_send` | 77-87 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_roomById` | 88-91 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_globalRoomIds` | 92-102 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_isGlobalRoomId` | 103-106 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_mains` | 107-110 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_childrenOf` | 111-114 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_normalizeSearch` | 115-121 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_compactSearch` | 122-125 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_statusMatches` | 126-131 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_orderedSearchScore` | 132-148 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_bestSearchId` | 149-163 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_topRootFor` | 164-178 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_currentRoomId` | 179-182 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_sortedRooms` | 183-190 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_ancestorPathFor` | 191-204 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_trimNavigatorPath` | 205-216 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_ensureNavigatorPath` | 217-237 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_preferredRootId` | 238-251 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_setNavigatorPath` | 252-263 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_applySearchFocus` | 264-279 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_tileFilterClass` | 280-293 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_collectSubtreeIds` | 294-304 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_displayedRoomsForSummary` | 305-317 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderSummary` | 318-337 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_isDescendant` | 338-354 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_statusDot` | 355-361 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderTabs` | 362-417 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_actionLabel` | 418-425 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderActionBar` | 426-451 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_selectCenter` | 452-462 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_addRoot` | 463-475 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_buildHierarchy` | 476 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `build` | 477-483 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_layoutCompactMap` | 484-491 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `layerTwoCount` | 492-495 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `blockWidth` | 496-499 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `assignStack` | 500-550 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_stretchMapToHeight` | 551-562 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_measureMapBounds` | 563-579 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_tileHtml` | 580-624 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_navigatorFilterClass` | 625-638 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_navigatorCardHtml` | 639-685 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderNavigator` | 686-751 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderTree` | 752-759 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderMapTree` | 760-997 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_applyZoom` | 998-1003 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyZoomReset` | 1004-1008 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologySetView` | 1009-1014 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyZoomBy` | 1015-1025 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_wireZoomPan` | 1026-1062 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderStandalone` | 1063-1084 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_applyClaimClasses` | 1085-1093 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_refreshActiveClaims` | 1094-1103 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_render` | 1104-1115 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_scheduleLayoutSettle` | 1116-1117 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `settleOnce` | 1118-1127 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_noteCanvasSize` | 1128-1137 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_wireLayoutObserver` | 1138-1163 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_afterGlobal` | 1164-1165 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyToggleActionMenu` | 1166-1171 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologySelectAction` | 1172-1177 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyClearAction` | 1178-1183 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_applyActionToTile` | 1184-1205 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyPin` | 1206-1210 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyRename` | 1211-1216 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyLifecycle` | 1217-1227 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDelete` | 1228-1240 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyAdd` | 1241-1251 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyAddChild` | 1252-1272 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_reparent` | 1273-1289 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyStartMove` | 1290-1296 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyStartLink` | 1297-1303 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyCancelMove` | 1304-1310 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDetach` | 1311-1317 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyTileClick` | 1318-1326 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyNavigatorSelect` | 1327-1335 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyOpenRoom` | 1336-1341 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyTabDragStart` | 1342-1353 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyTabDragOver` | 1354-1375 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyTabDragLeave` | 1376-1384 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyTabDrop` | 1385-1402 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDragStart` | 1403-1416 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDragOver` | 1417-1425 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDragLeave` | 1426-1429 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDropOnRoom` | 1430-1446 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyBandDragOver` | 1447-1456 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyBandDragLeave` | 1457-1460 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDropOnBand` | 1461-1482 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDragEnd` | 1483-1501 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_renderBanner` | 1502-1516 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyMakeRoot` | 1517-1521 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologySetFilter` | 1522-1529 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_topoNote` | 1530-1554 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_wrapNote` | 1555-1564 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `_onWorkspaceEvent` | 1565-1580 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyRefresh` | 1581-1631 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyInit` | 1632-1662 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyRowClick` | 1663 | code | Code block. |
| `memory/chatroom/static/js/chatroom.topology.js` | `topologyDropOnColumn` | 1664-1706 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_unlockAudio` | 37-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_cleanForTTS` | 50-59 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_setTTS` | 60-68 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_cancelTTSQueue` | 69-82 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_forceAutoPacingForTTS` | 83-99 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `toggleTTS` | 100-109 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_getAudioCtx` | 110-120 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_playWavBytes` | 121-137 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_isTTSJobStale` | 138-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_isTTSJobCurrent` | 142-145 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_queuedAtForTTS` | 146-150 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_sleep` | 151-154 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_createTTSChunkBuffer` | 155-181 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_decodeTTSRecord` | 182-196 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_readTTSNDJSON` | 197-200 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `pushLine` | 201-234 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_fetchTTSIntoBuffer` | 235-297 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_enqueueTTSFetch` | 298-309 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_enqueueTTSPlayback` | 310-313 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_playBufferedTTSChunks` | 314-328 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `playTTS` | 329-347 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `playKaraokeTTS` | 348-393 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_saveTtsVoicePrefs` | 394-398 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_buildVoiceList` | 399-425 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `previewVoice` | 426-437 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `openVoicePicker` | 438-445 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `closeVoicePicker` | 446-458 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_applyDecisionBarsVisibility` | 459-462 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_applyCompactMessageBubbles` | 463-466 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_compactBubbleMessagesPane` | 467-471 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_captureCompactBubbleScrollAnchor` | 472-493 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_restoreCompactBubbleScrollAnchor` | 494-496 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `restore` | 497-525 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `setKaraokeEnabled` | 526-532 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `setKaraokeMode` | 533-537 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `setKaraokeWPM` | 538-543 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `setDecisionBarsEnabled` | 544-549 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `setCompactMessageBubblesEnabled` | 550-557 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_initKaraokeControls` | 558-633 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_revealKaraokePart` | 634-642 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_scrollAfterKaraokeReveal` | 643-650 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_revealKaraokeSentence` | 651-654 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_revealKaraokeTimed` | 655-678 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_nuclearRevealKaraoke` | 679-692 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_setMicState` | 693-701 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_bestAudioMimeType` | 702-707 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_recordingFilename` | 708-713 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_transcribeMicBlob` | 714-723 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_insertTranscript` | 724-731 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_stopMicStream` | 732-740 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `toggleMic` | 741-792 | code | Code block. |
| `memory/chatroom/static/js/chatroom.voice.js` | `_wireVoiceControls` | 793-821 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_emitWorkspaceEvent` | 73-79 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_notifyClaimsWorkspaceHydrated` | 80-94 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadJsonMap` | 95-103 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadStringSet` | 104-113 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_saveStringSet` | 114-120 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pinnedIds` | 121-126 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pinnedItems` | 127-157 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_serializePinnedItem` | 158-166 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_savePinnedItems` | 167-209 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_syncPinnedToServer` | 210-226 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadPinnedFromServer` | 227-253 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadPreferenceFromServer` | 254-276 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_syncPreferenceToServer` | 277-292 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadTreeSelectionFromServer` | 293-311 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_savePinnedIds` | 312-322 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_movePinnedId` | 323-335 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pinWorkspaceAtTop` | 336-343 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_unpinWorkspace` | 344-352 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceTagsById` | 353-356 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_explicitTagsForWorkspace` | 357-364 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_normalizeTagPath` | 365-372 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pathSegment` | 373-379 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_branchPaths` | 380-388 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_safeFolderLabel` | 389-392 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderIdForPath` | 393-402 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_newFolderId` | 403-406 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceFolders` | 407-433 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceFolderById` | 434-445 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_saveWorkspaceFolders` | 446-468 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_saveWorkspaceFolderById` | 469-481 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderById` | 482-488 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderLabel` | 489-494 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceFolderId` | 495-498 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderChildren` | 499-503 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderHasDescendant` | 504-513 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceCountForFolder` | 514-530 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_directWorkspacesForFolder` | 531-538 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderDisplayPath` | 539-551 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderSelectOptionsHtml` | 552-554 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `walk` | 555-566 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_ensureFolderPath` | 567-583 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_findFolderPath` | 584-596 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_ensureFoldersFromLegacyBranches` | 597-625 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_moveWorkspaceToFolder` | 626-639 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_moveFolderToParent` | 640-650 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_roomFromUrl` | 651-654 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_isCollabSession` | 655-660 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_normalizeRoomId` | 661-664 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_globalRoomIds` | 665-673 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_isGlobalRoom` | 674-677 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setCollabAllowedRooms` | 678-687 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setCollabRoomPolicy` | 688-704 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setCollabBoundRoom` | 705-708 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_collabAllowedRooms` | 709-715 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_collabCanAccessRoom` | 716-721 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_collabScopeWorkspaces` | 722-730 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_initialRoomId` | 731-740 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `getCurrentRoomId` | 741-744 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `syncRoomBackgroundIdentity` | 745-763 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_helpRoomId` | 764-769 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_prepareHelpRoomSurface` | 770-780 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_setCurrentRoomId` | 781-788 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceTitle` | 789-799 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_isRootWorkspace` | 800-805 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_activeMainRootId` | 806-814 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_activeMainWorkspace` | 815-819 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_rootForWorkspace` | 820-831 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setWorkspaceMainRoot` | 832-841 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setRoomNameHint` | 842-855 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceMessageCount` | 856-861 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceMessageCountLabel` | 862-867 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceStatus` | 868-872 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerScopeRootId` | 873-879 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerScopedRoomIds` | 880-903 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_isHeaderScopedRoomId` | 904-910 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerActiveWorkspaces` | 911-938 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerClaimCountsByRoom` | 939-951 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerClaimCountForRoom` | 952-955 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerRowClaimCountForRoom` | 956-966 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerTotalClaims` | 967-970 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerActiveClaimItems` | 971-987 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerPendingClaimItems` | 988-1004 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_claimLabel` | 1005-1008 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_claimStatusLabel` | 1009-1016 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderClaimRow` | 1017-1040 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_headerClaimItemFromRow` | 1041-1055 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_focusClaimNavigation` | 1056-1072 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_retryClaimNavigationFocus` | 1073-1076 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `tryFocus` | 1077-1094 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_onClaimTileClick` | 1095-1106 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderWorkspaceRow` | 1107-1124 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_bindHeaderCounters` | 1125-1181 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderPanel` | 1182-1195 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderWorkspacePanel` | 1196-1199 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderClaimsPanel` | 1200-1203 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderPendingClaimsPanel` | 1204-1207 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderCounterPanels` | 1208-1214 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderCounters` | 1215-1316 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeHeaderWorkspacePanel` | 1317-1326 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeHeaderClaimsPanel` | 1327-1336 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeHeaderPendingClaimsPanel` | 1337-1346 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeHeaderCounterPanels` | 1347-1353 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleHeaderWorkspacePanel` | 1354-1367 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleHeaderClaimsPanel` | 1368-1381 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleHeaderPendingClaimsPanel` | 1382-1395 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `openHeaderClaimsCounter` | 1396-1401 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `refreshHeaderCounters` | 1402-1417 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `startHeaderCounterPolling` | 1418-1436 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_hydrateHeaderCompletedState` | 1437-1443 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_completionId` | 1444-1447 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_persistHeaderCompletedState` | 1448-1452 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_visibleHeaderCompletedNewIds` | 1453-1461 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderCompletedIndicator` | 1462-1475 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_clearHeaderCompletedNewState` | 1476-1484 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_applyHeaderCompletedItems` | 1485-1500 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_completionAgentLabel` | 1501-1505 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_completionTimeText` | 1506-1513 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderCompletedRow` | 1514-1537 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderHeaderCompletedList` | 1538-1563 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_loadRecentCompletions` | 1564-1584 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_focusCompletion` | 1585-1586 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `scrollToCompletion` | 1587-1606 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `consumeCompletionFocus` | 1607-1612 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `tryFocus` | 1613-1628 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `consumeClaimNavigationFocus` | 1629-1636 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_onCompletionTileClick` | 1637-1661 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeHeaderCompletedPanel` | 1662-1671 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleHeaderCompletedPanel` | 1672-1689 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_positionHeaderCompletedPanel` | 1690-1693 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_formatGb` | 1694-1698 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `loadWorkspaceResources` | 1699-1710 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `confirmWorkspaceSpawn` | 1711-1720 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspacePauseToggleHtml` | 1721-1729 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceActionButtonsHtml` | 1730-1742 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceTabHtml` | 1743-1759 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `syncMainWorkspaceTab` | 1760-1793 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `syncActiveWorkspaceTab` | 1794-1831 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `switchActiveWorkspaceTab` | 1832-1838 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `showActiveWorkspaceTabMenu` | 1839-1845 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_sortedWorkspaces` | 1846-1851 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_isPinned` | 1852-1855 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renderWorkspaceTabs` | 1856-1876 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_sidebarWorkspaceRowHtml` | 1877-1905 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_sidebarDividerHtml` | 1906-1922 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renderSidebarWorkspaceList` | 1923-1949 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_updateSidebarPinnedUnpinModeUi` | 1950-1960 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_setSidebarPinnedUnpinMode` | 1961-1965 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `togglePinnedUnpinMode` | 1966-1975 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarPinnedWorkspaceClick` | 1976-1991 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleSidebarWorkspaceView` | 1992-2009 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pinnedItemKey` | 2010-2013 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_pinnedDividerSectionRange` | 2014-2026 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_clearSidebarDropMarkers` | 2027-2032 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_sectionDividerId` | 2033-2036 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_sidebarDropIsNoop` | 2037-2047 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceDragStart` | 2048-2057 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceSectionDragStart` | 2058-2062 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceDragOver` | 2063-2073 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceDragLeave` | 2074-2078 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceDrop` | 2079-2109 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `sidebarWorkspaceDragEnd` | 2110-2116 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_archivedWorkspaces` | 2117-2122 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renderArchivedWorkspaceList` | 2123-2128 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceMatchesFilters` | 2129-2150 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDragStart` | 2151-2159 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceFolderDragStart` | 2160-2168 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDragOver` | 2169-2177 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_dragToken` | 2178-2187 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDropOnFolder` | 2188-2201 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDropOnBranch` | 2202-2205 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDropOnWorkspace` | 2206-2218 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceTreeDragEnd` | 2219-2224 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceManagerRowClick` | 2225-2230 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_folderPrompt` | 2231-2246 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeNodeActionsHtml` | 2247-2259 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeRootHtml` | 2260-2268 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeNodeButtonHtml` | 2269-2283 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeWorkspaceRowHtml` | 2284-2296 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeWorkspaceRowsHtml` | 2297-2303 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_treeChildrenHtml` | 2304-2318 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renderWorkspacesTree` | 2319-2345 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `addWorkspaceBranch` | 2346-2349 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `addWorkspaceFolder` | 2350-2353 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renameWorkspaceFolder` | 2354-2365 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `moveWorkspaceFolder` | 2366-2386 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `removeWorkspaceFolder` | 2387-2408 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `removeWorkspaceBranch` | 2409-2412 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `selectWorkspaceTreeNode` | 2413-2419 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_workspaceManagerRowHtml` | 2420-2453 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renderWorkspacesPage` | 2454-2489 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setWorkspacesFilter` | 2490-2495 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `toggleWorkspacePin` | 2496-2503 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `addPinnedWorkspaceDivider` | 2504-2513 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `addPinnedWorkspaceDividerBelow` | 2514-2527 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `removePinnedWorkspaceDivider` | 2528-2538 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `updatePinnedWorkspaceDivider` | 2539-2547 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `togglePinnedWorkspaceDivider` | 2548-2562 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `movePinnedWorkspace` | 2563-2568 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `movePinnedWorkspaceFromTab` | 2569-2577 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `resumeWorkspaceFromSidebar` | 2578-2586 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `pauseWorkspaceFromSidebar` | 2587-2595 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `editWorkspaceTags` | 2596-2599 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `editWorkspaceFolder` | 2600-2606 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setWorkspaceFolderFromSelect` | 2607-2613 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `loadWorkspaces` | 2614-2644 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_syncWorkspaceHeader` | 2645-2686 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `noteWorkspaceMessage` | 2687-2713 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_replaceRoomInUrl` | 2714-2720 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_resetRoomUi` | 2721-2739 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `switchToWorkspace` | 2740-2765 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_promptRootCodebaseRepo` | 2766-2794 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `createWorkspaceFromPrompt` | 2795-2828 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `renameWorkspace` | 2829-2863 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `archiveWorkspace` | 2864-2879 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `restoreWorkspace` | 2880-2895 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `pauseWorkspace` | 2896-2909 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `resumeWorkspace` | 2910-2925 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `deleteWorkspace` | 2926-2942 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `archiveWorkspaceFromTab` | 2943-2951 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `pauseWorkspaceFromTab` | 2952-2960 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `resumeWorkspaceFromTab` | 2961-2969 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_defaultForkTitle` | 2970-2979 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_renderForkAnchorHighlights` | 2980-2999 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_clearForkRangeAnchors` | 3000-3007 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `setForkRangeAnchor` | 3008-3025 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `openForkPreviewModal` | 3026-3056 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `closeForkPreviewModal` | 3057-3063 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `confirmForkFromPreview` | 3064-3100 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_closeWorkspaceContextMenu` | 3101-3107 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_onWorkspaceContextMenuOutside` | 3108-3112 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_onWorkspaceContextMenuKey` | 3113-3120 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_showWorkspaceContextMenu` | 3121-3159 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `showWorkspaceTabMenu` | 3160-3166 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `handleWorkspaceEvent` | 3167-3176 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `_initWorkspaceTreeResizer` | 3177-3186 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `applyWidth` | 3187-3203 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `browserCssScale` | 3204-3210 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `onMove` | 3211-3217 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `onUp` | 3218-3247 | code | Code block. |
| `memory/chatroom/static/js/chatroom.workspaces.js` | `workspaceBootstrap` | 3248-3345 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_loadRoomConfig` | 42-97 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_normalizePanelPane` | 98-103 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_panelSideForMode` | 104-109 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_isPanelPane` | 110-112 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_panelModeAllowed` | 113-119 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `isWorkshopRoomProfileActive` | 120-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_loadPanelState` | 134-151 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_savePanelState` | 152-178 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_resolveActivityRoom` | 179-181 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityRoomMatches` | 182-208 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentKey` | 209-211 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentColor` | 212-215 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentLabel` | 216-245 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityTimestampParts` | 246-256 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityTimestampHtml` | 257-261 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityTimestampText` | 262-267 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_markToolFinalized` | 268-274 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_consumeToolFinalized` | 275-310 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_turnState` | 311-328 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_resetAgentTurnState` | 329-332 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_parseStatusDate` | 333-338 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_monitorStatusTruthFor` | 339-370 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_applyStatusTruthToTurnState` | 371-394 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_refreshStatusTruth` | 395-414 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_ensureStatusTruthTimer` | 415-419 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_noteActivityForStrip` | 420-512 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_clearAgentStatusIndicator` | 513-520 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_noteAgentResumed` | 521-526 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_stripAgeText` | 527-534 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_stripStateFor` | 535-562 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `getAgentStatusSnapshot` | 563-565 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `isHumanAgent` | 566-600 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_ensureStatusStrip` | 601-613 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_statusMetaParts` | 614-618 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_statusMetaText` | 619-625 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_statusSignature` | 626-634 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_cloneStatusRow` | 635-646 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_stateTransitionKey` | 647-650 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_resolveQueuedChatStatusRows` | 651-746 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderStatusStrip` | 747-791 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPanelRows` | 792-810 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentParticipant` | 811-815 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentCanQuickControl` | 816-820 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentStatusText` | 821-831 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentActivityText` | 832-844 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentThinkingText` | 845-849 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentDotClass` | 850-854 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderQuickControl` | 855-867 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPidLine` | 868-878 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPanelPidBits` | 879-887 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPanelConnectionLight` | 888-915 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPanelActionButtons` | 916-926 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_agentPanelRuntimeNodes` | 927-949 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_layoutAgentPanelControls` | 950-993 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_ensureAgentPanelWired` | 994-1026 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderAgentPanel` | 1027-1042 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `openAgentPanel` | 1043-1050 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `closeAgentPanel` | 1051-1058 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderChatStatusBar` | 1059-1108 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_insertActivityRow` | 1109-1121 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_capActivityFeedRows` | 1122-1132 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityEventKey` | 1133-1145 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityOldestCursor` | 1146-1154 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityShouldLoadOlder` | 1155-1159 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_derivedActivityPaneForFeed` | 1160-1165 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_bindActivityHistoryScrollers` | 1166-1182 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_derivedActivityShouldLoadOlder` | 1183-1188 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_derivedActivityCursor` | 1189-1196 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_derivedActivitySeenKeys` | 1197-1201 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_loadDerivedActivityHistory` | 1202-1265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_ensureDerivedActivityHistory` | 1266-1271 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_loadOlderActivityEvents` | 1272-1317 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_mobileFeedRelocate` | 1318-1333 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_mobileFeedReturnHome` | 1334-1365 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_ensurePanelPaneHomes` | 1366-1412 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_visiblePanelPanes` | 1413-1422 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_applyPanelPaneWeights` | 1423-1439 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_syncPanelResizeHandles` | 1440-1455 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_bindPanelPaneResizeHandle` | 1456-1461 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `finishDrag` | 1462-1478 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `onMove` | 1479-1524 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_panelOpenSet` | 1525-1528 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_panelLastMode` | 1529-1532 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_setPanelLastMode` | 1533-1537 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_allOpenPanelPanes` | 1538-1541 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_syncPanelModeButtons` | 1542-1550 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderPanelDock` | 1551-1605 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `setPanelMode` | 1606-1628 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `syncWorkshopRoomProfile` | 1629-1668 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `navigateToWorkshopRoom` | 1669-1675 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `navigateToHelpRoom` | 1676-1682 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `activityBootstrap` | 1683-1695 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_connectActivitySSE` | 1696-1716 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_loadRecent` | 1717-1863 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_disconnectActivitySSE` | 1864-1868 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `setActivityRoomContext` | 1869-1916 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimAgentKey` | 1917-1920 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimText` | 1921-1924 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLines` | 1925-1928 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLineMatches` | 1929-1932 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLabelFromLine` | 1933-1949 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimIdentity` | 1950-1953 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLabelKey` | 1954-1957 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimKey` | 1958-1963 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimMessageIdentity` | 1964-1969 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimQueueIdentity` | 1970-1974 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimActivityIdentity` | 1975-1988 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimMessageDomId` | 1989-1992 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimTime` | 1993-1997 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimTimeText` | 1998-2007 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPhaseRank` | 2008-2028 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimStageIndex` | 2029-2043 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimStageStepper` | 2044-2060 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPhaseLabel` | 2061-2076 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPhaseDetail` | 2077-2092 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRoomDocCheckState` | 2093-2104 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRoomRequiresDocCheck` | 2105-2108 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimIsMilestonePhase` | 2109-2112 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimIsActivePhase` | 2113-2116 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimCapWorkSteps` | 2117-2129 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRowsFor` | 2130-2138 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimExistingByIdentity` | 2139-2144 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimEnsure` | 2145-2179 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimExisting` | 2180-2184 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimOpenExisting` | 2185-2188 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimOpenExistingForCompletion` | 2189-2204 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimClosedExistingForActivity` | 2205-2214 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimMergeRows` | 2215-2260 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimMergeAgentRows` | 2261-2266 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimAddStep` | 2267-2286 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPlanStartTime` | 2287-2290 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPlanCompleteTime` | 2291-2294 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimApplyPlanTimestamps` | 2295-2316 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimNoopCloseInfo` | 2317-2331 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimMs` | 2332-2336 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPlanWindow` | 2337-2347 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRowTimes` | 2348-2356 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLegacyRowMatchesPlanItem` | 2357-2366 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimLatestForAgent` | 2367-2386 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `resetClaimsTracker` | 2387-2394 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `reconcileClaimDocCheckState` | 2395-2411 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRenderStep` | 2412-2419 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimRenderCapNotice` | 2420-2430 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_claimPreferredMessageId` | 2431-2443 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_scrollClaimMessage` | 2444-2452 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_findClaimRow` | 2453-2459 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_focusClaimKey` | 2460-2478 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `scrollToRow` | 2479-2489 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderClaimsFeed` | 2490-2581 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `trackClaimMessage` | 2582-2640 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `trackClaimActivity` | 2641-2673 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `addStep` | 2674-2699 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `trackClaimPlanItem` | 2700-2727 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `addQueueStep` | 2728-2770 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `switchDiffSubtab` | 2771-2784 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_diffClaimLabel` | 2785-2790 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_diffTurnId` | 2791-2795 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_diffProtectedInfo` | 2796-2808 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_revertProtectedDiff` | 2809-2837 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_clearDiffPreviews` | 2838-2857 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_appendDiffEntry` | 2858-2938 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_showProtectedDiffToast` | 2939-2953 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderSplitDiff` | 2954-2981 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderFileDiff` | 2982-3006 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityToolSummary` | 3007-3049 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityDecodeUrlQuery` | 3050-3058 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityCurlSearchSummary` | 3059-3081 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityStripShellQuotes` | 3082-3089 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityPathTail` | 3090-3094 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityFullToolText` | 3095-3101 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityCodeRefsFromText` | 3102-3125 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityCodeRefsHtml` | 3126-3129 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityToggleExpanded` | 3130-3151 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityAttachExpandable` | 3152-3162 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityShellCommandSummary` | 3163-3185 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityToolDetail` | 3186-3193 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activitySummaryFileName` | 3194-3207 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_intentScore` | 3208-3223 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activitySummaryPhrase` | 3224-3243 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activitySummaryRawText` | 3244-3250 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activitySummaryChips` | 3251-3258 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activityClassifyResult` | 3259-3268 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderActivitySummary` | 3269-3327 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_scheduleActivitySummaryFinalize` | 3328-3347 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_activitySummaryFor` | 3348-3381 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_updateActivitySummary` | 3382-3430 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_hotEscape` | 3431-3439 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderHotMarkdown` | 3440-3492 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_syncMemorySubtabUi` | 3493-3504 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `switchMemorySubtab` | 3505-3560 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `loadHotMemory` | 3561-3586 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `loadShortMemory` | 3587-3612 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `loadRollupMemory` | 3613-3638 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `handleHotMemoryUpdated` | 3639-3647 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `handleShortMemoryUpdated` | 3648-3656 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `_renderActivityEvent` | 3657-3964 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `focusClaimByAgentLabel` | 3965-3970 | code | Code block. |
| `memory/chatroom/static/js/chatroom/activity.js` | `navigateClaimByQueueItem` | 3971-4039 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_generatedMediaUrl` | 17-21 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_generatedMediaKind` | 22-25 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_generatedMediaMime` | 26-41 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_generatedMediaPreview` | 42-51 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_generatedMediaArtifactHtml` | 52-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `initArtifactZoom` | 67-73 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `applyArtifactTransform` | 74-90 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `dist` | 91-177 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `loadArtifactsFromDB` | 178-202 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `extractArtifact` | 203-223 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `renderArtifactContent` | 224-262 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `addArtifact` | 263-304 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `renderArtifactHistory` | 305-317 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `showArtifact` | 318-328 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `artifactZoomBy` | 329-333 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `artifactZoomReset` | 334-342 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `artifactToggleFullscreen` | 343-353 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `artifactOpenInNewTab` | 354-403 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_clearArtifactPanelBadge` | 404-411 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_showArtifactsPane` | 412-423 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_restorePanelContent` | 424-445 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `openRightPanel` | 446-463 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `openArtifactPanel` | 464-483 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `closeRightPanel` | 484-500 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `closeArtifactPanel` | 501-527 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `onMove` | 528-539 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `onUp` | 540-572 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `toggleRightPanel` | 573-585 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `toggleArtifactPanel` | 586-589 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `setArtifactPanelTab` | 590-598 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_loadArtifactPanelItems` | 599-640 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_showArtifactPanel` | 641-649 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_apanelApplyTransform` | 650-658 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `apanelZoomBy` | 659-663 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `apanelZoomReset` | 664-673 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `apanelToggleFullscreen` | 674-683 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `apanelOpenInNewTab` | 684-727 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_renderArtifactInPanel` | 728-806 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_downloadArtifactPanel` | 807-830 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `_deleteArtifactPanel` | 831-850 | code | Code block. |
| `memory/chatroom/static/js/chatroom/artifacts.js` | `undoArtifactDelete` | 851-922 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_escapeHtml` | 19-21 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_formatText` | 22-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_escapeAttr` | 25-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_renderMarkdownContent` | 28-39 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_appendSystem` | 40-42 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_formatSize` | 43-45 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_replaceArray` | 46-51 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_attachmentMimeForName` | 52-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_attachmentFromUpload` | 63-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_filesUploadUrl` | 73-79 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_pasteSnippetLabel` | 80-85 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_storePastedTextViewerBlock` | 86-91 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_pastedTextSummaryHtml` | 92-98 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_pastedTextBlockHtml` | 99-107 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `closeChatContentFullscreen` | 108-116 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `_ensureChatContentFullscreen` | 117-152 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `openChatContentFullscreen` | 153-177 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `openPastedTextFullscreen` | 178-192 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `openChatImageFullscreen` | 193-203 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `clearPastedTextViewerBlocks` | 204-207 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `deletePastedTextViewerBlock` | 208-212 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `renderPendingAttachments` | 213-249 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `removePendingAttachment` | 250-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `removeComposerPasteSnippet` | 261-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `uploadFileAndStash` | 266-293 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `rememberTextPaste` | 294-302 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `buildPasteAwareMetadata` | 303-330 | code | Code block. |
| `memory/chatroom/static/js/chatroom/attachments.js` | `renderPasteAwareText` | 331-420 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_msgNodes` | 17-22 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_msgId` | 23-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_author` | 29-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_nodeText` | 37-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_snippet` | 47-57 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_esc` | 58-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_highlight` | 67-82 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_render` | 83-105 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_run` | 106-129 | code | Code block. |
| `memory/chatroom/static/js/chatroom/chat_search.js` | `_init` | 130-173 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_el` | 11-12 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_stageText` | 13-25 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_statusClass` | 26-32 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_actionLabel` | 33-39 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_render` | 40-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_esc` | 67-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `_refresh` | 73-79 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `openCliAuthModal` | 80-88 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `closeCliAuthModal` | 89-94 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `cliAuthSetup` | 95-102 | code | Code block. |
| `memory/chatroom/static/js/chatroom/cli_auth.js` | `cliAuthSaveKey` | 103-126 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_targetMentionRe` | 13-16 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_leadingAgentMention` | 17-21 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_ensureTargetStyle` | 22-40 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_ensureTargetBar` | 41-64 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_renderComposerTarget` | 65-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_setComposerTargetState` | 77-81 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_removeManagedMention` | 82-86 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_syncComposerTargetFromText` | 87-100 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `setComposerTarget` | 101-113 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `clearComposerTarget` | 114-125 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `sendMessage` | 126-185 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `_renderPendingHumanMessage` | 186-246 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `autoResizeMsgInput` | 247-251 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `renderMentionPopup` | 252-258 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `insertMention` | 259-270 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `hideMentionPopup` | 271-276 | code | Code block. |
| `memory/chatroom/static/js/chatroom/composer.js` | `bindComposerControls` | 277-360 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_currentAssetVersionTag` | 8-12 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_serverAssetVersionTag` | 13-17 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_reloadForAssetMismatch` | 18-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_checkClientBuildVersions` | 28-41 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_dispatchCurrentRoomId` | 42-50 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_dispatchPayloadMatchesRoom` | 51-55 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `_messageCountsForWorkspace` | 56-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `handleEvent` | 63-442 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dispatch.js` | `registerTransportHandlers` | 443-469 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `loadScript` | 15-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `scEnsureMermaid` | 28-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `scEnsureD3` | 37-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `readAppZoom` | 44-54 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `setViewportHeight` | 55-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `scheduleViewportHeight` | 72-87 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssDeltaX` | 88-91 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssDeltaY` | 92-95 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssWidthFromClientX` | 96-99 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssHeightFromClientY` | 100-103 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssViewportWidth` | 104-107 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `cssRightWidthFromClientX` | 108-111 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `elementCssWidth` | 112-118 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `elementCssHeight` | 119-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `readBubbleFontSize` | 134-160 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `applyMsgZoom` | 161-165 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `persistBubbleFontSize` | 166-177 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_tabPaneId` | 178-182 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_isMobileTabZoomable` | 183-186 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_mobileTabZoomKey` | 187-190 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_readMobileTabZoom` | 191-199 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_applyMobileTabZoom` | 200-209 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_persistMobileTabZoom` | 210-233 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_activeTab` | 234-237 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_applyActiveMobileTabZoom` | 238-243 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `_shouldSkipMobileContentZoom` | 244-253 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `touchDist` | 254-290 | code | Code block. |
| `memory/chatroom/static/js/chatroom/dom.js` | `getTouchDist` | 291-358 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingEscape` | 7-12 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingJsArg` | 13-20 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingOpenFile` | 21-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingIgnoreKey` | 28-37 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingLoadIgnored` | 38-53 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingSaveIgnored` | 54-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingVisibleHits` | 61-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingActiveEntries` | 67-74 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingSortedEntries` | 75-83 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `encodingScan` | 84-140 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `_encodingRender` | 141-186 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `encodingIgnoreHit` | 187-197 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `encodingRepairFile` | 198-233 | code | Code block. |
| `memory/chatroom/static/js/chatroom/encoding_panel.js` | `encodingRepairAll` | 234-249 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `el` | 34-37 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `escapeHtml` | 38-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `normalizePath` | 47-54 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `repoSlug` | 55-61 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `roomId` | 62-69 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `workspaceRootPath` | 70-78 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `workspaceDocPath` | 79-86 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `ensureWorkspaceDocItem` | 87-101 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `openWorkspaceDefault` | 102-110 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `storageKey` | 111-117 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `serverStateKey` | 118-121 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `itemKey` | 122-125 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `activeItem` | 126-129 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `basename` | 130-134 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `dirname` | 135-140 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `treeEntryLabel` | 141-144 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `collabUrl` | 145-156 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelTreeUrl` | 157-160 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelTreeFileIcon` | 161-208 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `isMarkdownPath` | 209-212 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `currentContent` | 213-217 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `setCurrentContent` | 218-223 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderMarkdownContent` | 224-236 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `prismLangFor` | 237-243 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `splitHighlightedLines` | 244-250 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `requestLanguageAutoload` | 251-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `highlightedLineHtml` | 266-280 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `parseDiffChangedRanges` | 281-286 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `flushDeletionAnchor` | 287-321 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `mergeRanges` | 322-334 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `diffEventKey` | 335-338 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `diffStatsHtml` | 339-348 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderDiffBody` | 349-371 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `diffHistoryHtml` | 372-390 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `lineForRange` | 391-405 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `clearDiffHistoryMarkers` | 406-412 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `clearAnnotationMarkers` | 413-419 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `insertDiffHistoryMarker` | 420-446 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `hydrateDiffBodies` | 447-469 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `mergeHistoryEvents` | 470-481 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `rangesForEvent` | 482-497 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderDiffHistoryPager` | 498-516 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderDiffHistoryEvents` | 517-545 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `annotationGranularity` | 546-554 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `annotationRowHtml` | 555-571 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `insertAnnotationMarker` | 572-586 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadReadOnlyAnnotations` | 587-634 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadLineDecorations` | 635-640 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadDiffHistory` | 641-678 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `readErrorMessage` | 679-692 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `setStatus` | 693-699 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `ensureTreeBrowser` | 700-732 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `setTreeButtonState` | 733-739 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderTreeMessage` | 740-745 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `treePathPrefixes` | 746-754 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `applyTreeActivePath` | 755-768 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `setTreeActivePath` | 769-773 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderTreeHeader` | 774-785 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderTreeEntries` | 786-858 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadTreeChildren` | 859-873 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadWorkspaceTree` | 874-898 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelToggleTreeBrowser` | 899-910 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelHideTreeBrowser` | 911-917 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `showWorkspaceRoot` | 918-932 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadState` | 933-990 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `saveState` | 991-998 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `trimWorkingSet` | 999-1006 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderToolbar` | 1007-1041 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `ensurePopover` | 1042-1058 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderText` | 1059-1103 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `renderImage` | 1104-1114 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `loadActiveFile` | 1115-1187 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `addOrFocusFile` | 1188-1206 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `openPanel` | 1207-1217 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `openFileInPanel` | 1218-1229 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelBootstrap` | 1230-1256 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelResetForRoom` | 1257-1282 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelTogglePicker` | 1283-1287 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelSelect` | 1288-1297 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelMove` | 1298-1307 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelRemove` | 1308-1330 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelJumpToLine` | 1331-1352 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelCopyPath` | 1353-1367 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelOpenCodebase` | 1368-1381 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelOpenInNewTab` | 1382-1395 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelToggleFullscreen` | 1396-1402 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelSaveGuardStatus` | 1403-1447 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelSave` | 1448-1493 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelFormat` | 1494-1526 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelToggleRenderMode` | 1527-1536 | code | Code block. |
| `memory/chatroom/static/js/chatroom/files_panel.js` | `filesPanelEdit` | 1537-1565 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `esc` | 44-52 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `fmt` | 53-56 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `agentClass` | 57-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `buildFloatingAvatar` | 61-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `appendFloatingModelBadge` | 72-85 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `injectStyle` | 86-127 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `buildAgent` | 128-208 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `viewport` | 209-215 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `rectsOverlap` | 216-222 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `pointNearRect` | 223-230 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `rectFromPlacement` | 231-241 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `currentHighlightRect` | 242-246 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `candidatePlacements` | 247-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `placementScore` | 266-281 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `bestPlacement` | 282-304 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `currentAgentRect` | 305-317 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `applyPlacement` | 318-327 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `relayoutAgent` | 328-341 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `scheduleAvoidance` | 342-357 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `freezeAgent` | 358-363 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `targetComposer` | 364-373 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `_showBubble` | 374-392 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `showAgent` | 393-402 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `hideAgent` | 403-415 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `showBubble` | 416-420 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `hideBubble` | 421-436 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `mirror` | 437-455 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `currentRoomId` | 456-461 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `topChatVisible` | 462-466 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `shouldMirrorProjection` | 467-471 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `mirrorProjection` | 472-476 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `clearSurface` | 477-480 | code | Code block. |
| `memory/chatroom/static/js/chatroom/floating_agents.js` | `init` | 481-510 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_el` | 23-26 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_esc` | 27-32 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_attr` | 33-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_topicColor` | 37-40 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_tokens` | 41-44 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_highlight` | 45-56 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_regexEsc` | 57-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_snippet` | 61-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_formatWhen` | 77-83 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_setStatus` | 84-90 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_setTopicsStatus` | 91-97 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_fetchJson` | 98-104 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_searchChatroom` | 105-120 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_searchArchive` | 121-138 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_loadTopics` | 139-161 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_runSearch` | 162-196 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_render` | 197-225 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_renderTopics` | 226-267 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_messageNode` | 268-271 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_wait` | 272-275 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_waitForHistory` | 276-278 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `finish` | 279-285 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `onHistory` | 286-294 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_pageUntilMessage` | 295-309 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_jumpToResult` | 310-333 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_jumpToRoom` | 334-343 | code | Code block. |
| `memory/chatroom/static/js/chatroom/global_search.js` | `_init` | 344-445 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `addGovernanceItem` | 3-31 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `addPlanItem` | 32-45 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `formatGovTimestamp` | 46-57 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `isGovernanceLifecycleNoise` | 58-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `compactGovValue` | 63-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govPreviewLabel` | 73-78 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `buildGovPayloadPreview` | 79-92 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govActionType` | 93-96 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govAttentionQueryTextForItem` | 97-108 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govAttentionQueryTextForTask` | 109-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govLaneLabel` | 134-137 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govTaskLane` | 138-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `getGovActionEntries` | 142-146 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `govActionEntryPassesFilters` | 147-153 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `taskQueueEntryPassesAttentionFilters` | 154-160 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderGovAttentionFilterState` | 161-175 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `updateGovAttentionFilterState` | 176-182 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `setGovAttentionFilter` | 183-189 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `clearGovAttentionFilters` | 190-196 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderGovernanceTab` | 197-267 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `loadTasksFromQueue` | 268-293 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderTaskCard` | 294-329 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderTaskQueue` | 330-373 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `approveTask` | 374-393 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `rejectTask` | 394-413 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `switchGovSubtab` | 414-431 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `loadBuildBacklog` | 432-446 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `buildBacklogEntryPassesFilters` | 447-462 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderGovBuildFilterState` | 463-473 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `setGovBuildFilter` | 474-479 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `clearGovBuildFilters` | 480-485 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderBuildBacklog` | 486-553 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `parseChangeLogPayloadText` | 554-565 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `buildGovResolvedPreview` | 566-573 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `addGovResolvedItem` | 574-606 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `renderGovResolved` | 607-651 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `loadGovResolvedFromDB` | 652-663 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `updateGovSidebarBadge` | 664-684 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `resolveGov` | 685-769 | code | Code block. |
| `memory/chatroom/static/js/chatroom/governance.js` | `resolvePlan` | 770-821 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `createInvite` | 3-26 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `loadCollabbook` | 27-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `openCollabDetail` | 50-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `stars` | 72-104 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `loadCollabChat` | 105-126 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `saveCollabNotes` | 127-142 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `showExitSurvey` | 143-175 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `rateQ` | 176-184 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `submitExitSurvey` | 185 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guest.js` | `getR` | 186-226 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `cleanToken` | 16-20 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `cleanLabel` | 21-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `activeTabName` | 25-32 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `isVisibleElement` | 33-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `visibleFeatureIds` | 44-56 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `noteEvent` | 57-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `noteTab` | 63-69 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `labelFor` | 70-74 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `noteClick` | 75-85 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `snapshot` | 86-93 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `canSend` | 94-99 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `sendHeartbeat` | 100-114 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `scheduleSend` | 115-120 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `wrapSwitchTab` | 121-134 | code | Code block. |
| `memory/chatroom/static/js/chatroom/guide_context.js` | `start` | 135-164 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `esc` | 31-33 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `fmtTime` | 34-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `el` | 37-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `injectStyle` | 44-78 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `build` | 79-119 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `setStatus` | 120-125 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `_clearList` | 126-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `mirror` | 134-173 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `send` | 174-189 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `open` | 190-196 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `close` | 197-201 | code | Code block. |
| `memory/chatroom/static/js/chatroom/help_dock.js` | `toggle` | 202-211 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `ensureLayer` | 7-21 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `clearHighlight` | 22-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `escAttr` | 37-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `targetForFeature` | 44-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `isVisible` | 50-58 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `showFailure` | 59-89 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `appZoom` | 90-94 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `toLayerRect` | 95-108 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `drawHighlight` | 109-174 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `ensurePulseStyle` | 175-182 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `highlightFeature` | 183-204 | code | Code block. |
| `memory/chatroom/static/js/chatroom/highlight.js` | `handleHighlightCommand` | 205-222 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_normalizeModeId` | 6-15 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_modeInfo` | 16-22 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_refreshHostModeStatus` | 23-32 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_renderModeChrome` | 33-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_populateHostModeSelect` | 50-63 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_initModeCatalog` | 64-85 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_setModeBadge` | 86-91 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_renderAutoFollowUp` | 92-106 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `toggleAutoFollowUp` | 107-113 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_syncRoastSelfieRow` | 114-140 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `uploadRoastSelfie` | 141-162 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `refanoutRoastSelfie` | 163-176 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `_applyHostCollabPresence` | 177-182 | code | Code block. |
| `memory/chatroom/static/js/chatroom/host_controls.js` | `hostLeaveCollabSession` | 183-217 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_isLandscapeCollapseMode` | 2-5 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_isPortraitComposerMode` | 6-9 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_syncComposerToggleButton` | 10-25 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `toggleLandscapeCollapse` | 26-38 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `onchange` | 39-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `onportrait` | 50-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_isMobileSidebar` | 73-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_leftSidebarPanel` | 77-81 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_leftSidebarToggle` | 82-86 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_isLeftSidebarOpen` | 87-96 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_positionPanelEdgeTabs` | 97-123 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_syncChatScrollControls` | 124-152 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `syncChatLaneMetrics` | 153-162 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `scheduleChatLaneMetricsSync` | 163-169 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `syncChatLaneState` | 170-180 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_syncPanelEdgeTabs` | 181-195 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_setLeftSidebarOrder` | 196-200 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `syncLeftSidebars` | 201-232 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `toggleLeftSidebar` | 233-242 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `toggleSidebar` | 243-248 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `togglePinnedWorkspaceSidebar` | 249-254 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `closeLeftSidebars` | 255-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `_scSaveSidebarWidth` | 266-286 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `applySavedWidth` | 287-298 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `finishDrag` | 299-338 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `onMove` | 339-424 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `onMove` | 425-431 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `onUp` | 432-490 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `clearBodyUserSelect` | 491-514 | code | Code block. |
| `memory/chatroom/static/js/chatroom/layout.js` | `snapRootScroll` | 515-528 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderImageStackHtml` | 11-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderArtifactMediaHtml` | 29-41 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderMediaBodyHtml` | 42-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderMessageFooterHtml` | 50-53 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_scIsCollabMode` | 54-132 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_scImageStackOutsideClick` | 133-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setLastChatContextMsg` | 142-150 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setLastIncitingMsg` | 151-176 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_armThinkingTimer` | 177-183 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_clearThinkingTimer` | 184-190 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `clearThinkingIndicator` | 191-198 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_currentRoomId` | 199-203 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_payloadRoomId` | 204-206 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_belongsToCurrentRoom` | 207-209 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_helpRoomId` | 210-216 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_isChatTabVisible` | 217-224 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_hasActiveNonChatSidePanel` | 225-255 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_shouldMirrorSameRoomHelpFloater` | 256-262 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_receiptDisplayName` | 263-270 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_isAiReceiptBubbleSender` | 271-274 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_orderedReceiptNames` | 275-291 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderAiSeenReceiptForMessage` | 292-316 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_seedAiSeenReceiptsFromMessage` | 317-331 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `handleAiSeenReceipt` | 332-349 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_clearAllThinkingState` | 350-363 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_emitThinkingStatus` | 364-369 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_visibleThinkingText` | 370-374 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_touchThinkingBubble` | 375-377 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_topicBoundaryColor` | 378-380 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_ensureTopicBoundaryMinimap` | 381-438 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_topicBoundaryNodes` | 439-442 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_jumpToTopicBoundary` | 443-448 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_lastMsgIdBefore` | 449-459 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_forkFromTopicBoundary` | 460-476 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_renderTopicBoundaryPanel` | 477-528 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_openTopicBoundaryPanel` | 529-536 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_closeTopicBoundaryPanel` | 537-543 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_toggleTopicBoundaryPanel` | 544-547 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_maybeCloseTopicBoundaryPanel` | 548-553 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_updateTopicBoundaryViewport` | 554-575 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_refreshTopicBoundaryMinimap` | 576-630 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_scheduleTopicBoundaryMinimapRefresh` | 631-635 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_messageSpeakerKey` | 636-642 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_isAiContextMessage` | 643-648 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_isReplyToDifferentSpeaker` | 649-659 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_formatElapsedCompact` | 660-669 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_messageContextLabel` | 670-690 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_appendMessageContextBadge` | 691-697 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_directMessageChild` | 698-701 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_ensureMessageFooter` | 702-715 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_trimRuntimeBadgeLabel` | 716-720 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_runtimeLabelForSender` | 721-731 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_messageRuntimeLabel` | 732-743 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setMessageModelBadge` | 744-763 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_appendMessageModelBadge` | 764-770 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `hydrateMessageModelBadges` | 771-785 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_rememberChatContextMsg` | 786-808 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_shouldRenderThinkerInChat` | 809-823 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_collabHasCodebaseAccess` | 824-829 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_sanitizeForCollab` | 830-864 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `handleThinkingIndicator` | 865-888 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `handleThinkingDelta` | 889-906 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `handleToolStream` | 907-924 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `handleWorkUpdate` | 925-962 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_avatarSlugFor` | 963-967 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_buildAvatarEl` | 968-973 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `showInitial` | 974-990 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_maybeAttachAvatar` | 991-1017 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_drkActionClass` | 1018-1025 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_drkBarDisplayLabel` | 1026-1031 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_decisionDetailValue` | 1032-1042 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_appendDecisionDetailRow` | 1043-1052 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_buildDecisionDetailEl` | 1053-1073 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_decisionBarKey` | 1074-1081 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_decisionBarParticipant` | 1082-1087 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_findDecisionBarInCurrentTurn` | 1088-1113 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_silentBarAnchorIds` | 1114-1123 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_findSilentBarAnchorEl` | 1124-1138 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_findAnchoredBarForMerge` | 1139-1148 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_insertAnchoredSilentBar` | 1149-1161 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_queuePendingSilentBar` | 1162-1166 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_clearPendingSilentBars` | 1167-1170 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_flushPendingSilentBarsFor` | 1171-1183 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_buildDrkEventBarEl` | 1184-1203 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `toggleDetails` | 1204-1220 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_handleDrkEventMessage` | 1221-1262 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_appendDecisionEventDetail` | 1263-1299 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setChatHistoryBaseline` | 1300-1302 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_capChatMessageNodes` | 1303-1306 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_evictOldest` | 1307-1353 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_resetOlderPagination` | 1354-1361 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_oldestRenderedMsgId` | 1362-1367 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_prependOlderMessages` | 1368-1385 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `loadOlderMessages` | 1386-1417 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `appendMessage` | 1418-1675 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `walk` | 1676-1944 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `appendSystemMessage` | 1945-1952 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_decodeBasicHtmlEntities` | 1953-1961 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_splitCodeRefLine` | 1962-1968 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_normalizeCodeRefTarget` | 1969-1994 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_codeRefAnchor` | 1995-2005 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_linkifyMarkdownCodeRefs` | 2006-2023 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_mentionHighlightRegex` | 2024-2034 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `formatText` | 2035-2077 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `escapeHtml` | 2078-2083 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `escapeAttr` | 2084-2087 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `renderMarkdown` | 2088-2111 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setJumpToLatestVisible` | 2112-2116 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `scrollToBottom` | 2117 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `snap` | 2118-2130 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `bindMessageScroll` | 2131-2149 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `clearSeenIds` | 2150-2157 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `resetMessageContext` | 2158-2163 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `resetMessagesForReconnect` | 2164-2177 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `resetMessagesForHistoryReplay` | 2178-2188 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_setReplyingTo` | 2189-2194 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `setReply` | 2195-2209 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `clearReply` | 2210-2215 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `scrollToMsg` | 2216-2235 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqRoomId` | 2236-2241 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqStorageKey` | 2242-2246 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqExtractQuestion` | 2247-2267 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqLoad` | 2268-2271 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqSave` | 2272-2296 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `_qqPrune` | 2297-2301 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `qqRender` | 2302-2338 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `qqDismiss` | 2339-2345 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `qqResetForRoom` | 2346-2350 | code | Code block. |
| `memory/chatroom/static/js/chatroom/messages.js` | `qqCheckMessage` | 2351-2449 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadRoomId` | 10-15 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadRoomQuery` | 16-19 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadQueryForRoom` | 20-23 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadOrderStorageKey` | 24-27 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadEl` | 28-31 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSetStatus` | 32-38 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadDiskLabel` | 39-44 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadEditorContent` | 45-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSetEditorContent` | 50-55 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadNameValue` | 56-60 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadNormalizePath` | 61-66 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadBasename` | 67-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadDirname` | 72-77 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadNoteKey` | 78-84 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadCurrentKey` | 85-88 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSourceRoomFor` | 89-92 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadRoomChoices` | 93-102 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadResolveRoomChoice` | 103-114 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSetNameLocked` | 115-121 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSubtitle` | 122-131 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadLoadOrder` | 132-140 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSaveOrder` | 141-170 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadSortNotes` | 171-183 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadRenderPicker` | 184-195 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadEnsureImportButton` | 196-213 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadEnsurePopover` | 214-230 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `_notepadRenderPreview` | 231-239 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadBootstrap` | 240-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadResetForRoom` | 261-273 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadRefreshList` | 274-287 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadNew` | 288-299 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadLoad` | 300-320 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadSave` | 321-357 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadTogglePicker` | 358-362 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadMove` | 363-372 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadUnpin` | 373-397 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadImport` | 398-446 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadFormat` | 447-487 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadToggleRender` | 488-504 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadToggleFullscreen` | 505-514 | code | Code block. |
| `memory/chatroom/static/js/chatroom/notepad.js` | `notepadOpenInNewTab` | 515-529 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `showDrkToast` | 3-19 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_floorRoomId` | 20-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_floorUrl` | 25-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_updatePacingOnRowVisibility` | 29-35 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `setPacingMode` | 36-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `setPacingOnSeconds` | 47-56 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `setPacingAutoWPM` | 57-70 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_prettyFloorName` | 71-75 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_renderFloorBadge` | 76-103 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `refreshFloorState` | 104-139 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_startFloorPolling` | 140-158 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_populateModelDropdownsFromManifest` | 159-191 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_applyEffortConstraintsForModel` | 192-231 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_cacheRuntimeSelect` | 232-236 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_restoreRuntimeSelectsFromCache` | 237-248 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_setRuntimeSelectValue` | 249-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_finishRuntimeSelectHydration` | 266-274 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_normalizeAgentServiceTier` | 275-279 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_agentModelValue` | 280-284 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_modelSupportsFastMode` | 285-292 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_applyCollabAgentControlLock` | 293-315 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_setAgentFastModeButton` | 316-332 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `toggleAgentFastMode` | 333-346 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `switchAgentConfig` | 347-380 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_agentServiceTierValue` | 381-385 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_collectAgentRuntimeConfig` | 386-393 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `applyAgentSettingsToAllRooms` | 394-418 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `pollApiHealthThenReload` | 419-420 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `httpsFallbackHealth` | 421-424 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `jumpToHttpsFallback` | 425-427 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `tick` | 428-447 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `scheduleNextPoll` | 448-459 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_cacheBustReload` | 460-475 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_hardRefreshNoticeUrl` | 476-480 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_sendHardRefreshNotice` | 481-498 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `hardRefreshPage` | 499-507 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `restartApiOnly` | 508-523 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `shutdownSC` | 524-545 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `restartChatroom` | 546-566 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `restartAllLiveAgents` | 567-584 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `setStaggerDelay` | 585-597 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ops_controls.js` | `_hydrateStaggerInput` | 598-635 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `noop` | 3-4 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `stopEvent` | 5-10 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `asText` | 11-14 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `createOrderedPopover` | 15-29 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `setHidden` | 30-36 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `documentMouseDown` | 37-44 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `documentKeyDown` | 45-48 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `render` | 49-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `open` | 142-155 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `close` | 156-163 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ordered_popover.js` | `toggle` | 164-179 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `_participantDisplayList` | 7-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `renderMobileParticipants` | 25-38 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `renderParticipants` | 39-95 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `kickCollab` | 96-107 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `toggleMute` | 108-119 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `killAgent` | 120-123 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `restartAgent` | 124-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `restartAgentResume` | 134-137 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `toggleAgentPause` | 138-141 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `_sendAgentControl` | 142-157 | code | Code block. |
| `memory/chatroom/static/js/chatroom/participants.js` | `refreshParticipantsSnapshot` | 158-208 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_esc` | 17-24 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_room` | 25-28 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_shortTime` | 29-42 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_statusBadge` | 43-46 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_notifyClaims` | 47-58 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_actions` | 59-76 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_renderItem` | 77-104 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_onDispatch` | 105-134 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_onReject` | 135-158 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_bindActions` | 159-190 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_sortRows` | 191-202 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_itemBelongsToCurrentRoom` | 203-207 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_updateStagedBadge` | 208-214 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_render` | 215-236 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_findPlanRow` | 237-243 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `focusPlanItemById` | 244-262 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `scrollToRow` | 263-274 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `loadPlanBoard` | 275-301 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `resetPlanBoard` | 302-309 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `refreshIfVisible` | 310-320 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `handlePlanItemUpdated` | 321-331 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_renderAutoPickup` | 332-341 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_toggleAutoPickup` | 342-358 | code | Code block. |
| `memory/chatroom/static/js/chatroom/plan.js` | `_bindAutoPickup` | 359-381 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_loadDebugFilterState` | 61-81 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_saveDebugFilterState` | 82-119 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugFamily` | 120-133 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugTag` | 134-186 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptContextLaneMeta` | 187-211 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptHotMemoryMeta` | 212-229 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugActorKey` | 230-242 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugIdentityName` | 243-247 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugActorLabel` | 248-260 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugActorChip` | 261-265 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugTargetFor` | 266-272 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugSourceFor` | 273-286 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugRouteFor` | 287-341 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugPrimaryText` | 342-352 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugTitle` | 353-381 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugNormalizeAction` | 382-385 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugGroupKey` | 386-393 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugLabelFromAction` | 394-399 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugRememberGroup` | 400-409 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugRegisterFilterKey` | 410-431 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugSeedStaticActors` | 432-442 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugSeedRegistryFilters` | 443-454 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugRegistryEntryFor` | 455-458 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugRegistryMetaFor` | 459-481 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_debugRefreshExistingEntryMeta` | 482-491 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_ensureDebugRegistryLoaded` | 492-531 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_bufferPreamble` | 532-550 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_tryAbsorbPreamble` | 551-564 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugSection` | 565-570 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `promptDebugPayloadText` | 571-583 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `isPromptDebugVisible` | 584-589 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `appendPromptDebug` | 590-678 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `updatePromptDebugBadge` | 679-683 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_promptShouldLoadOlder` | 684-688 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_bindPromptHistoryScroller` | 689-696 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `loadPromptDebugLog` | 697-739 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_buildDebugFilters` | 740-746 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_rebuildDebugFilterBar` | 747-759 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `chipEnabled` | 760-763 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `makeChip` | 764-789 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `makeGroup` | 790-808 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `groupCollapsed` | 809-814 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `addGroupCollapse` | 815-818 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `syncLabel` | 819-835 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `addGroupToggle` | 836-840 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `syncLabel` | 841-933 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `_applyDebugFilters` | 934-946 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `hideDropAlertToast` | 947-955 | code | Code block. |
| `memory/chatroom/static/js/chatroom/prompt_debug.js` | `showDropAlertToast` | 956-996 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `showEmojiPicker` | 14-48 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `hideEmojiPicker` | 49-52 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `toggleReaction` | 53-65 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `updateReactionStrip` | 66-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `renderReactionStrip` | 73-87 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `attachReactionHandlers` | 88-100 | code | Code block. |
| `memory/chatroom/static/js/chatroom/reactions.js` | `loadBulkReactions` | 101-140 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `isCollabMode` | 41-49 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `collabGuestToken` | 50-57 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `shouldProxyCollabUrl` | 58-68 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `collabProxyUrl` | 69-72 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `collabUrl` | 73-127 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `replaceArray` | 128-132 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `clearArray` | 133-137 | code | Code block. |
| `memory/chatroom/static/js/chatroom/state.js` | `resetObject` | 138-153 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `_hydrateTabIframe` | 2-10 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `switchTab` | 11-100 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `switchCodebaseSubtab` | 101-126 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `restoreActiveTab` | 127-154 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `updateTabBadge` | 155-161 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `_mobileSurfaceValue` | 162-167 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `_mobileRoomTitle` | 168-173 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `_mobileRoomRows` | 174-177 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `pushRoom` | 178-197 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `_syncMobileRoomSelect` | 198-214 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `syncMobileNavState` | 215-228 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `mobileSelectSurface` | 229-237 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `mobileSelectRoom` | 238-246 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `openMobilePinnedWorkspaces` | 247-252 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `toggleMobileControlsMenu` | 253-258 | code | Code block. |
| `memory/chatroom/static/js/chatroom/tabs.js` | `closeMobileControlsMenu` | 259-284 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `openThinkerSession` | 2-17 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `loadThinkerSessions` | 18-39 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `setThinkerChartMode` | 40-59 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `switchThinkerSubtab` | 60-68 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `thinkerSessionTimestamp` | 69-74 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `thinkerSortNewestFirst` | 75-78 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderThinkerSidebar` | 79-198 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `workshopSessionStatusMap` | 199-202 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `workshopCategoryLabel` | 203-207 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderWorkshopPanels` | 208-212 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderWorkshopSessionsPane` | 213-249 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderWorkshopOutputPane` | 250-292 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `switchWorkshopSessionSubtab` | 293-296 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `selectWorkshopSession` | 297-301 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderThinkerSessionDetail` | 302-356 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderThinkerSpeakerGroups` | 357-385 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderSessionMessagesAsChat` | 386-405 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `selectSession` | 406-422 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `dismissQueuedSession` | 423-430 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `renderSessionActions` | 431-452 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `_getOrCreateWorkshopBanner` | 453-466 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `syncWorkshopInteractionState` | 467-472 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `_clearState` | 473-509 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `sessionAction` | 510-533 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `sendSessionMessage` | 534-553 | code | Code block. |
| `memory/chatroom/static/js/chatroom/thinker.js` | `finalizeSession` | 554-618 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `_setSocket` | 22-31 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `_setTransportConnected` | 32-39 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `transportSocket` | 40-43 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `isTransportOpen` | 44-48 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `sendJson` | 49-55 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `resetReconnectDelay` | 56-59 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `setTransportHandlers` | 60-63 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `_currentRoomId` | 64-71 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `_chatroomWsUrl` | 72-88 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `connect` | 89-169 | code | Code block. |
| `memory/chatroom/static/js/chatroom/transport.js` | `disconnect` | 170-238 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `_isCollabMode` | 37-45 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `_safeGet` | 46-50 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `_safeSet` | 51-62 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `cached` | 63-75 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `hydrated` | 76-79 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `load` | 80-102 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `save` | 103-124 | code | Code block. |
| `memory/chatroom/static/js/chatroom/ui_prefs.js` | `markHydrated` | 125-136 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `formatSize` | 2-9 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `inlineImageMarker` | 10-13 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `maxInlineImageRefFromAttachments` | 14-22 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `maxInlineImageRefFromText` | 23-34 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `removeFirstInlineImageMarker` | 35-44 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `_getInputEl` | 45-50 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `getNextInlineImageRef` | 51-65 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `cleanOrphanedImageMarkers` | 66-96 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `bindUploadPasteHandlers` | 97-165 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `_insertAtCursor` | 166-190 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `_currentInlineReferenceMax` | 191-198 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `_removeInlineReference` | 199-223 | code | Code block. |
| `memory/chatroom/static/js/chatroom/uploads.js` | `_uploadAndInsertInline` | 224-324 | code | Code block. |
| `memory/chatroom/static/js/chatroom/workspace_demo.js` | `loadWorkspaceDemoData` | 35-58 | code | Code block. |
| `memory/chatroom/static/js/chatroom/workspace_demo.js` | `unloadWorkspaceDemoData` | 59-77 | code | Code block. |
| `memory/chatroom/static/js/chatroom/workspace_demo.js` | `toggleWorkspaceDemo` | 78-86 | code | Code block. |
| `memory/chatroom/v2_runtime_store.py` | `_loads_json` | 26-34 | function | Function block. |
| `memory/chatroom/v2_runtime_store.py` | `_actor_type` | 37-44 | function | Function block. |
| `memory/chatroom/v2_runtime_store.py` | `_scope_for_actor` | 47-61 | function | Function block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store` | 64-650 | class | Small v2-native persistence surface used by ``ChatroomServer``. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.__init__` | 67-69 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.start` | 71-72 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.close` | 74-75 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._connect` | 77-81 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._is_locked_error` | 84-86 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._with_lock_retry` | 88-98 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._row_to_message` | 101-133 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.load_recent_messages` | 135-136 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._load_recent_messages_sync` | 138-151 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.load_recent_messages_for_room` | 153-154 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._load_recent_messages_for_room_sync` | 156-171 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.has_chat_messages_for_room` | 173-175 | async method | Return True if the room has any non-deleted chat messages. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._has_chat_messages_for_room_sync` | 177-192 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.has_help_intro_blocking_messages_for_room` | 194-199 | async method | Return True if room history should block the empty-HELP intro wake. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._is_help_intro_startup_chatter` | 202-224 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._has_help_intro_blocking_messages_for_room_sync` | 226-248 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.save_message` | 250-253 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.prune_doc_status_for_room` | 255-258 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._prune_doc_status_for_room_sync` | 260-279 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._save_message_sync` | 281-318 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.save_artifact_companion` | 320-343 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.list_artifacts` | 345-359 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._collab_artifact_since` | 361-370 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._list_artifacts_sync` | 372-424 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.soft_delete_artifact` | 426-427 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.restore_artifact` | 429-431 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._set_artifact_deleted_sync` | 433-471 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.update_message_metadata` | 473-478 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._update_message_metadata_sync` | 480-500 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._get_message_context_sync` | 502-521 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.get_message_reactions` | 523-524 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._prune_reaction_events_sync` | 526-533 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._get_message_reactions_sync` | 535-558 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.get_bulk_reactions` | 560-564 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.get_bulk_reactions_sync` | 566-596 | method | Method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store.toggle_reaction` | 598-609 | async method | Async method block. |
| `memory/chatroom/v2_runtime_store.py` | `ChatroomV2Store._toggle_reaction_sync` | 611-650 | method | Method block. |
| `memory/chatroom/wake_routing.py` | `pick_untagged_lead` | 42-65 | function | Return (lead_id, secondary_id) for an untagged human message. |
| `memory/chatroom/wake_routing.py` | `tagged_wake_targets` | 68-76 | function | Return AI targets for a tagged room message, excluding the sender. |
| `memory/chatroom/wake_routing.py` | `is_standalone_claim` | 79-81 | function | Function block. |
| `memory/chatroom/wake_routing.py` | `is_standalone_claim_complete` | 84-90 | function | True for messages whose first line is a standalone [CLAIM COMPLETE: ...]. |
| `memory/chatroom/wake_routing.py` | `is_standalone_claim_started` | 93-103 | function | True for messages whose first line is a standalone [CLAIM STARTED: ...]. |
| `memory/chatroom/wake_routing.py` | `is_protocol_control_message` | 106-123 | function | True for claim/protocol control lines that must not be floor-parked. |
| `memory/chatroom/wake_routing.py` | `_guide_framing_context` | 126-141 | function | Function block. |
| `memory/chatroom/wake_routing.py` | `record_claim_broadcast` | 144-150 | function | Record a standalone CLAIM so later competing claims can be arbitrated. |
| `memory/chatroom/wake_routing.py` | `track_claim_lifecycle` | 153-183 | function | Maintain `_open_claims_by_room` so claim-notice suppression knows who is currently busy with their own claim. |
| `memory/chatroom/wake_routing.py` | `maybe_block_competing_claim` | 186-239 | async function | Return True if `msg` is a standalone CLAIM that loses to a recent peer CLAIM. |
| `memory/chatroom/wake_routing.py` | `maybe_enqueue_claim_notice` | 242-290 | async function | If `msg` is a standalone CLAIM line from an AI, notify every other AI. |
| `memory/chatroom/wake_routing.py` | `enqueue_tagged_wake_events` | 293-380 | async function | Enqueue central wake events for a tagged human/guest/AI message. |
| `memory/chatroom/wake_routing.py` | `enqueue_untagged_human_wake_events` | 383-425 | async function | Enqueue central wake events for an untagged human/guest message. |
| `memory/chatroom/wake_routing.py` | `enqueue_untagged_ai_peer_wake` | 428-480 | async function | Server-authored peer wake for an UNTAGGED AI message. |
| `memory/chatroom/wake_routing.py` | `delayed_wake_event_enqueue` | 483-493 | async function | Enqueue a wake event after a server-owned stagger delay. |
| `memory/chatroom/wake_routing.py` | `delayed_secondary_untagged_wake_enqueue` | 496-535 | async function | Build and enqueue the secondary untagged-wake at its own wake-time. |
| `memory/chatroom/workspace_actions.py` | `json_loads_or` | 31-40 | function | Function block. |
| `memory/chatroom/workspace_actions.py` | `message_metadata_from_envelope` | 43-53 | function | Function block. |
| `memory/chatroom/workspace_actions.py` | `history_row_to_message_payload` | 56-81 | function | Function block. |
| `memory/chatroom/workspace_actions.py` | `workspace_history_payloads` | 84-106 | function | Function block. |
| `memory/chatroom/workspace_actions.py` | `_refresh_workspace_explorer_index` | 109-115 | async function | Async function block. |
| `memory/chatroom/workspace_actions.py` | `handle_workspace_action` | 118-268 | async function | Async function block. |
| `memory/chatroom/workspace_explorer_index.py` | `WorkspaceExplorerEntry` | 30-38 | class | Class block. |
| `memory/chatroom/workspace_explorer_index.py` | `WorkspaceExplorerResult` | 42-54 | class | Class block. |
| `memory/chatroom/workspace_explorer_index.py` | `WorkspaceExplorerResult.to_dict` | 51-54 | method | Method block. |
| `memory/chatroom/workspace_explorer_index.py` | `refresh_workspace_explorer_index` | 57-107 | function | Refresh root index files and local Windows shortcuts for workspaces. |
| `memory/chatroom/workspace_explorer_index.py` | `_build_entries` | 110-136 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_ascii_label` | 139-143 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_safe_filename` | 146-150 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_unique_shortcut_name` | 153-167 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_render_markdown` | 170-199 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_render_html` | 202-247 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_md_cell` | 250-251 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_folder_link` | 254-263 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_write_windows_shortcuts` | 266-285 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_create_lnk_files` | 288-329 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_ps_quote` | 332-333 | function | Function block. |
| `memory/chatroom/workspace_explorer_index.py` | `_remove_stale_shortcuts` | 336-345 | function | Function block. |
| `memory/chatroom/workspace_message_counts.py` | `_has_column` | 12-13 | function | Function block. |
| `memory/chatroom/workspace_message_counts.py` | `_help_anvil_gated` | 16-40 | function | True only while the HELP/home room has an active, unrevealed intro gate. |
| `memory/chatroom/workspace_message_counts.py` | `count_participant_messages` | 43-65 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `now_iso` | 23-24 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `validate_room_id` | 27-37 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_root` | 40-44 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `archived_workspace_root` | 47-51 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_memory_root` | 54-58 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_hot_path` | 61-62 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_short_memory_path` | 65-66 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_notes_root` | 69-73 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_artifacts_root` | 76-77 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_generated_media_root` | 80-81 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_json_path` | 84-85 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_doc_path` | 88-89 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `ensure_workspace_doc` | 170-180 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `ensure_workspace_root` | 183-222 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `update_workspace_title` | 225-241 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `archive_workspace_root` | 244-270 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `restore_workspace_root` | 273-296 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `pause_workspace_root` | 299-318 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `resume_workspace_root` | 321-336 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `delete_workspace_root` | 339-348 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `workspace_env` | 351-372 | function | Function block. |
| `memory/chatroom/workspace_paths.py` | `current_room_id` | 375-376 | function | Function block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager` | 43-395 | class | Spawn/stop/reap for workspace agent trios, one room at a time. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.__init__` | 46-72 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.live_pid_handles_impl` | 76-93 | method | Recover live, identity-verified handles from per-room PID files. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.participant_processes_impl` | 95-105 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.ensure_tracked` | 107-112 | method | Adopt live PID-file handles for an untracked room (post-restart). |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.track_curator` | 114-115 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.windowless_python_exe` | 120-129 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.subprocess_kwargs` | 132-140 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.launch_process` | 142-163 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager._participant_command` | 166-190 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.spawn_trio` | 194-254 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.spawn_participant` | 256-278 | method | Spawn one workspace-local participant without touching sibling rooms. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.stop_participant` | 280-349 | method | Stop exactly one participant process in one workspace room and verify it is gone. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.reap_trio` | 351-364 | method | Method block. |
| `memory/chatroom/workspace_processes.py` | `WorkspaceProcessManager.resource_snapshot` | 366-395 | method | Method block. |
| `memory/chatroom/workspace_rollup.py` | `_hot_item_lines` | 65-70 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_entry_id` | 73-81 | function | Extract the [h-NN]/[s-NN] style id from a memory bullet, if present. |
| `memory/chatroom/workspace_rollup.py` | `_read_text` | 84-90 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_brief_path` | 93-94 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_brief_state_path` | 97-98 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_workspace_title` | 101-110 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_make_item` | 117-140 | function | Build a provenance-stamped memory item. |
| `memory/chatroom/workspace_rollup.py` | `collect_local_hot_items` | 147-164 | function | Read a room's own HOT.md into provenance-stamped local-origin items. |
| `memory/chatroom/workspace_rollup.py` | `collect_local_short_items` | 167-184 | function | Read a room's own Short_Memory.md into provenance-stamped local-origin items. |
| `memory/chatroom/workspace_rollup.py` | `_tail` | 191-194 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_line_text` | 197-198 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_memory_summary_text` | 201-205 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_clip_text` | 208-212 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_clip_lines` | 215-219 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_extract_markdown_section` | 222-249 | function | Return one markdown section body by heading text, or empty when absent. |
| `memory/chatroom/workspace_rollup.py` | `extract_workspace_doc_brief` | 252-266 | function | Extract WORKSPACE_DOC.md's authored Upward Brief section only. |
| `memory/chatroom/workspace_rollup.py` | `collect_recent_topics` | 269-306 | function | Return recent Curator topic boundary titles/summaries, newest last. |
| `memory/chatroom/workspace_rollup.py` | `_brief_hash` | 309-314 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `collect_child_briefs` | 317-335 | function | Read direct children's UPWARD_BRIEF files. |
| `memory/chatroom/workspace_rollup.py` | `_summarize_child_brief` | 338-357 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `render_upward_brief` | 360-422 | function | Render a bounded per-room upward brief. |
| `memory/chatroom/workspace_rollup.py` | `_render_error_upward_brief` | 425-458 | function | Render a bounded, visible failure marker for one room's rollup brief. |
| `memory/chatroom/workspace_rollup.py` | `write_upward_brief` | 461-486 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `write_upward_brief_isolated` | 489-521 | function | Write one room's brief without letting its render failure abort siblings. |
| `memory/chatroom/workspace_rollup.py` | `write_upward_briefs_bottom_up` | 524-540 | function | Generate child briefs before the parent brief. |
| `memory/chatroom/workspace_rollup.py` | `write_all_upward_briefs` | 543-575 | function | Backfill briefs for every non-archived room, child-before-parent where possible. |
| `memory/chatroom/workspace_rollup.py` | `_extract_brief_hash` | 578-582 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_read_json` | 585-590 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_claim_count` | 593-598 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_child_brief_hashes` | 601-606 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_brief_source_state` | 609-616 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_env_int` | 619-625 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `should_generate_upward_brief` | 628-684 | function | Deterministic pause gate for brief refresh. |
| `memory/chatroom/workspace_rollup.py` | `maybe_write_upward_brief_on_pause` | 687-692 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `dedup_items` | 699-720 | function | Reject same normalized text or same (origin_workspace_id, origin_item_id). |
| `memory/chatroom/workspace_rollup.py` | `_children_of` | 727-735 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `compute_up_export` | 738-776 | function | A room's upward export: its bounded UPWARD_BRIEF as one routed unit. |
| `memory/chatroom/workspace_rollup.py` | `_over_sources_for_target` | 783-805 | function | Return enabled OVER edges that deliver memory INTO room_id. |
| `memory/chatroom/workspace_rollup.py` | `compute_inbox` | 808-850 | function | Compute what flows INTO room_id: children UP-exports + OVER-imports. |
| `memory/chatroom/workspace_rollup.py` | `render_inbox_markdown` | 857-888 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_routed_view_has_content` | 891-899 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `_safe_write` | 906-922 | function | Write content only if changed. |
| `memory/chatroom/workspace_rollup.py` | `rebuild_room_views` | 929-1013 | function | Regenerate ROLLUP_INBOX.md + MEMORY_TOPOLOGY.json for a single room. |
| `memory/chatroom/workspace_rollup.py` | `rebuild_main_rollup` | 1020-1065 | function | Regenerate HELP's routed rollup view from its direct children + OVER links. |
| `memory/chatroom/workspace_rollup.py` | `rebuild_all` | 1072-1110 | function | Rebuild materialized views for every non-archived room, then Main. |
| `memory/chatroom/workspace_rollup.py` | `_append_proof` | 1113-1121 | function | Function block. |
| `memory/chatroom/workspace_rollup.py` | `read_routed_view` | 1128-1144 | function | Return (content, source_path) of the routed view to inject for a room. |
| `memory/chatroom/workspace_topology.py` | `_now_iso` | 19-20 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `_is_help_room` | 23-24 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `normalize_text` | 31-38 | function | Normalize HOT item text for dedup comparison within a rendered target. |
| `memory/chatroom/workspace_topology.py` | `is_duplicate_in_target` | 41-58 | function | Return (is_dup, reason) for a candidate item against a rendered target. |
| `memory/chatroom/workspace_topology.py` | `get_all_ancestor_ids` | 65-88 | function | Walk the parent chain and return all ancestor workspace IDs. |
| `memory/chatroom/workspace_topology.py` | `validate_parent_change` | 91-136 | function | Validate a proposed parent change. |
| `memory/chatroom/workspace_topology.py` | `set_workspace_parent` | 143-175 | function | Set or clear the parent of a workspace. |
| `memory/chatroom/workspace_topology.py` | `get_topology` | 182-256 | function | Return a snapshot of the full workspace routing topology. |
| `memory/chatroom/workspace_topology.py` | `create_memory_edge` | 263-337 | function | Create an OVER cross-link between two workspaces. |
| `memory/chatroom/workspace_topology.py` | `get_memory_edge` | 340-345 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `list_memory_edges` | 348-370 | function | List OVER cross-links, optionally filtered to edges touching workspace_id. |
| `memory/chatroom/workspace_topology.py` | `update_memory_edge` | 373-435 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `delete_memory_edge` | 438-456 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `_row_to_edge` | 459-474 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `preview_parent_change` | 481-523 | function | Return a preview of the routing effect of a proposed parent change. |
| `memory/chatroom/workspace_topology.py` | `get_room_route_info` | 530-601 | function | Return routing information for a single room (inspector panel data). |
| `memory/chatroom/workspace_topology.py` | `get_topology_debug_json` | 608-609 | function | Function block. |
| `memory/chatroom/workspace_topology.py` | `queue_delivery_item` | 616-646 | function | Queue a memory item for delivery to a paused room. |
| `memory/chatroom/workspace_topology.py` | `clear_delivery_queue` | 649-664 | function | Delete all queued delivery items for a room WITHOUT returning them. |
| `memory/chatroom/workspace_topology.py` | `flush_delivery_queue` | 667-698 | function | Retrieve and clear all queued delivery items for a room (the 'dump' on resume). |
| `memory/chatroom/workspace_topology.py` | `_log_topology_event` | 705-728 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_seedable_msg_type_clause` | 39-41 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_now_iso` | 44-45 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `ensure_permanent_rooms` | 48-70 | function | Idempotently seed the two permanent rooms (home + Workshop) at first boot. |
| `memory/chatroom/workspaces_store.py` | `_row_to_workspace` | 73-92 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_normalize_repo_slug` | 95-99 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `create_workspace` | 102-144 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `get_workspace` | 147-153 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `list_workspaces` | 156-171 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `list_active_workspaces` | 174-181 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `rename_workspace` | 184-194 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `archive_workspace` | 197-211 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `restore_workspace` | 214-225 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `pause_workspace` | 228-244 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `resume_workspace` | 247-263 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `set_workspace_doc_enabled` | 266-282 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `set_workspace_codebase_repo` | 285-302 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `resolve_workspace_codebase_repo` | 305-337 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `delete_workspace` | 340-353 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_has_column` | 356-357 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_message_id_match_sql` | 360-363 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_message_id_match_params` | 366-369 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_message_public_id_expr` | 372-375 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_ensure_workspace_fork_seeds` | 378-393 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_seed_reference_rows_for_bounds` | 396-424 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_write_workspace_fork_seed_refs` | 427-447 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `_backfill_workspace_fork_seed_refs` | 450-478 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `create_fork` | 481-554 | function | Create a workspace seeded with messages from a source-room range. |
| `memory/chatroom/workspaces_store.py` | `get_workspace_history` | 557-617 | function | Compose [seed + native] rendered history for a workspace. |
| `memory/chatroom/workspaces_store.py` | `_ensure_user_preferences` | 620-629 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `get_preference` | 632-642 | function | Function block. |
| `memory/chatroom/workspaces_store.py` | `set_preference` | 645-655 | function | Function block. |
| `memory/codebase/authors.py` | `_hsl_color` | 40-75 | function | Return a CSS hex color for an HSL triple. |
| `memory/codebase/authors.py` | `_hash_hue` | 95-104 | function | Deterministic hue from the agent string, drawn from a curated palette. |
| `memory/codebase/authors.py` | `_normalize_agent` | 107-108 | function | Function block. |
| `memory/codebase/authors.py` | `color_for_author` | 111-146 | function | Return color metadata for a single agent string. |
| `memory/codebase/authors.py` | `build_registry` | 149-170 | function | Return ``{"authors": {agent: meta}, "version": 1}`` for observed agents. |
| `memory/codebase/diff_ledger.py` | `record_section_attributions` | 46-99 | function | Insert per-section rows for one diff event. |
| `memory/codebase/diff_ledger.py` | `_is_allowed_workspace_runtime_diff_path` | 102-113 | function | Function block. |
| `memory/codebase/diff_ledger.py` | `_safe_repo_path` | 116-140 | function | Resolve a repo-relative path, refusing traversal outside the repo root. |
| `memory/codebase/diff_ledger.py` | `read_file` | 143-170 | function | Read a file by repo-relative path, returning text + computed sections. |
| `memory/codebase/diff_ledger.py` | `_event_from_row` | 173-184 | function | Function block. |
| `memory/codebase/diff_ledger.py` | `list_diffs_for_file` | 187-251 | function | Return chronological diff events for a file, each with section attributions. |
| `memory/codebase/diff_ledger.py` | `get_diff_event_for_file` | 254-300 | function | Return one uncapped diff event for a file after path and repo checks. |
| `memory/codebase/diff_ledger.py` | `list_diffs_for_section` | 303-351 | function | Return chronological diff events touching one section. |
| `memory/codebase/diff_ledger.py` | `section_summary_for_file` | 354-420 | function | Return current-known sections + edit count per section for gutter chips. |
| `memory/codebase/diff_ledger.py` | `write_human_edit` | 423-482 | function | Apply a human edit. |
| `memory/codebase/diff_meta.py` | `diff_stats` | 23-79 | function | Return added/removed line counts plus first changed line in the new file. |
| `memory/codebase/diff_meta.py` | `changed_ranges` | 82-127 | function | Return merged new-file line ranges touched by a unified diff. |
| `memory/codebase/diff_meta.py` | `section_diff_stats` | 130-198 | function | Stats for a diff scoped to a section's [start, end] line range. |
| `memory/codebase/diff_meta.py` | `detect_language` | 280-292 | function | Map a path to a CodeMirror/Monaco language id, or ``"plaintext"``. |
| `memory/codebase/diff_meta.py` | `attach_diff_stats` | 295-319 | function | Mutate-and-return helper: stamp ``stats`` onto each event dict in place. |
| `memory/codebase/repo_indexing.py` | `_utc_now` | 26-27 | function | Function block. |
| `memory/codebase/repo_indexing.py` | `_log_path` | 30-31 | function | Function block. |
| `memory/codebase/repo_indexing.py` | `_append_log` | 34-39 | function | Function block. |
| `memory/codebase/repo_indexing.py` | `_write_if_changed` | 42-48 | function | Function block. |
| `memory/codebase/repo_indexing.py` | `generate_repo_indexes` | 51-102 | function | Synchronously regenerate `_INDEX.md` files for one registered repo. |
| `memory/codebase/repo_indexing.py` | `_run_index_job` | 105-117 | async function | Async function block. |
| `memory/codebase/repo_indexing.py` | `schedule_repo_index` | 120-130 | function | Schedule an index refresh for a repo binding without blocking the caller. |
| `memory/codebase/save_guard.py` | `GuardStatus` | 23-40 | class | Class block. |
| `memory/codebase/save_guard.py` | `GuardStatus.to_dict` | 30-40 | method | Method block. |
| `memory/codebase/save_guard.py` | `SaveGuardResult` | 44-57 | class | Class block. |
| `memory/codebase/save_guard.py` | `SaveGuardResult.to_dict` | 51-57 | method | Method block. |
| `memory/codebase/save_guard.py` | `LanguageGuard` | 65-67 | class | Class block. |
| `memory/codebase/save_guard.py` | `_status` | 86-87 | function | Function block. |
| `memory/codebase/save_guard.py` | `_cwd` | 90-91 | function | Function block. |
| `memory/codebase/save_guard.py` | `_run_command` | 94-111 | function | Function block. |
| `memory/codebase/save_guard.py` | `_trim_output` | 114-115 | function | Function block. |
| `memory/codebase/save_guard.py` | `_looks_missing` | 118-130 | function | Function block. |
| `memory/codebase/save_guard.py` | `_which` | 133-134 | function | Function block. |
| `memory/codebase/save_guard.py` | `_prettier_base_command` | 138-151 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_with_command` | 154-174 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_python` | 177-195 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_prettier` | 198-207 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_json` | 210-217 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_go` | 220-224 | function | Function block. |
| `memory/codebase/save_guard.py` | `_format_rust` | 227-231 | function | Function block. |
| `memory/codebase/save_guard.py` | `_check_python` | 234-241 | function | Function block. |
| `memory/codebase/save_guard.py` | `_check_json` | 244-257 | function | Function block. |
| `memory/codebase/save_guard.py` | `_check_toml` | 260-267 | function | Function block. |
| `memory/codebase/save_guard.py` | `_check_node` | 270-295 | function | Function block. |
| `memory/codebase/save_guard.py` | `_prettier_parse_status` | 298-305 | function | Function block. |
| `memory/codebase/save_guard.py` | `_check_prettier` | 308-309 | function | Function block. |
| `memory/codebase/save_guard.py` | `_unsupported_formatter` | 312-313 | function | Function block. |
| `memory/codebase/save_guard.py` | `_unsupported_syntax` | 316-317 | function | Function block. |
| `memory/codebase/save_guard.py` | `apply_save_guard` | 332-359 | function | Return save content plus deterministic formatter/checker statuses. |
| `memory/codebase/section_indexer.py` | `Section` | 27-32 | class | Class block. |
| `memory/codebase/section_indexer.py` | `_normalize` | 50-51 | function | Function block. |
| `memory/codebase/section_indexer.py` | `_load_block_rows` | 54-85 | function | Return all Block Map rows as (target_relpath, label, kind, start, end). |
| `memory/codebase/section_indexer.py` | `find_sections_for_file` | 88-140 | function | Return sections for a file from the closest containing `_INDEX.md` Block Map. |
| `memory/codebase/section_indexer.py` | `parse_hunk_ranges` | 143-159 | function | Extract (start, end) line ranges in the post-edit file from a unified diff. |
| `memory/codebase/section_indexer.py` | `attribute_hunks` | 162-190 | function | Return one (section, hunk_start, hunk_end) per (hunk, touched section) pair. |
| `memory/codebase/ui_preferences.py` | `_db_path` | 25-26 | function | Function block. |
| `memory/codebase/ui_preferences.py` | `_ensure_table` | 40-49 | function | Function block. |
| `memory/codebase/ui_preferences.py` | `get_preference` | 52-75 | function | Return ``{"key","value","is_default","updated_at"}`` for ``key``. |
| `memory/codebase/ui_preferences.py` | `set_preference` | 78-112 | function | Upsert ``key`` -> JSON-encoded ``value``. |
| `memory/codebase/ui_preferences.py` | `all_preferences` | 115-138 | function | Return every persisted preference plus defaults for missing keys. |
| `memory/connectors/claude_code_connector.py` | `ClaudeCodeConnector` | 30-119 | class | Ingests parsed CC sessions through the governance chain. |
| `memory/connectors/claude_code_connector.py` | `ClaudeCodeConnector.__init__` | 33-40 | method | Method block. |
| `memory/connectors/claude_code_connector.py` | `ClaudeCodeConnector.is_already_ingested` | 42-49 | async method | Check if a session was already ingested via change_log. |
| `memory/connectors/claude_code_connector.py` | `ClaudeCodeConnector.ingest_session` | 51-119 | async method | Ingest a single CC session as pending governance proposals. |
| `memory/connectors/claude_code_parser.py` | `CCMessage` | 46-52 | class | A single message from a Claude Code session. |
| `memory/connectors/claude_code_parser.py` | `CCSession` | 56-83 | class | Parsed Claude Code session with scoring metadata. |
| `memory/connectors/claude_code_parser.py` | `_extract_assistant_text` | 86-116 | function | Extract readable text from an assistant message. |
| `memory/connectors/claude_code_parser.py` | `_extract_user_text` | 119-141 | function | Extract text from a user message. |
| `memory/connectors/claude_code_parser.py` | `parse_session_file` | 144-243 | function | Parse a single JSONL session file into a CCSession. |
| `memory/connectors/claude_code_parser.py` | `_score_session` | 246-283 | function | Score a session by substance signals. |
| `memory/connectors/claude_code_parser.py` | `format_for_librarian` | 286-345 | function | Format a CC session for Librarian ingestion. |
| `memory/connectors/claude_connector.py` | `ClaudeConnector` | 30-133 | class | Ingests parsed Claude conversations through the governance chain. |
| `memory/connectors/claude_connector.py` | `ClaudeConnector.__init__` | 40-47 | method | Method block. |
| `memory/connectors/claude_connector.py` | `ClaudeConnector.is_already_ingested` | 49-56 | async method | Check if a conversation was already ingested via change_log. |
| `memory/connectors/claude_connector.py` | `ClaudeConnector.ingest_conversation` | 58-133 | async method | Ingest a single Claude conversation as pending governance proposals. |
| `memory/connectors/claude_parser.py` | `ClaudeMessage` | 60-65 | class | A single message from a Claude conversation. |
| `memory/connectors/claude_parser.py` | `ClaudeConversation` | 69-83 | class | Parsed Claude conversation with scoring metadata. |
| `memory/connectors/claude_parser.py` | `_extract_message_text` | 86-142 | function | Extract readable text from a Claude message. |
| `memory/connectors/claude_parser.py` | `parse_conversation` | 145-217 | function | Parse a single conversation object from the Claude export. |
| `memory/connectors/claude_parser.py` | `_score_conversation` | 220-263 | function | Score a conversation by substance signals. |
| `memory/connectors/claude_parser.py` | `parse_export_file` | 266-290 | function | Parse a Claude conversations.json export file. |
| `memory/connectors/claude_parser.py` | `format_for_librarian` | 293-325 | function | Format a Claude conversation for Librarian ingestion. |
| `memory/connectors/codex_session_parser.py` | `_project_slug_from_cwd` | 22-37 | function | Function block. |
| `memory/connectors/codex_session_parser.py` | `_text_from_event_payload` | 40-53 | function | Function block. |
| `memory/connectors/codex_session_parser.py` | `_text_from_response_item` | 56-80 | function | Function block. |
| `memory/connectors/codex_session_parser.py` | `parse_session_file` | 83-198 | function | Parse a Codex rollout JSONL file into the shared transcript session type. |
| `memory/connectors/document_parser.py` | `DocumentChunk` | 29-34 | class | A chunk of a document sized for Librarian processing. |
| `memory/connectors/document_parser.py` | `Document` | 38-47 | class | A parsed design document ready for ingestion. |
| `memory/connectors/document_parser.py` | `_clean_title` | 50-56 | function | Derive a human-readable title from filename. |
| `memory/connectors/document_parser.py` | `_read_text_file` | 59-63 | function | Read a plain text or markdown file. |
| `memory/connectors/document_parser.py` | `_read_pdf_file` | 66-86 | function | Read a PDF file using pdfplumber. |
| `memory/connectors/document_parser.py` | `_chunk_text` | 89-149 | function | Split text into chunks at paragraph boundaries. |
| `memory/connectors/document_parser.py` | `parse_document` | 152-203 | function | Parse a single document file into a Document object. |
| `memory/connectors/document_parser.py` | `format_chunk_for_librarian` | 206-228 | function | Format a document chunk for Librarian extraction. |
| `memory/connectors/email_client.py` | `EmailMessage` | 28-45 | class | Parsed email message. |
| `memory/connectors/email_client.py` | `EmailClient` | 48-561 | class | Async IMAP/SMTP email client using stdlib wrapped in thread executor. |
| `memory/connectors/email_client.py` | `EmailClient.__init__` | 55-72 | method | Method block. |
| `memory/connectors/email_client.py` | `EmailClient.is_configured` | 75-77 | method | Check if email credentials are set. |
| `memory/connectors/email_client.py` | `EmailClient.test_connection` | 79-88 | async method | Test IMAP connection and return status. |
| `memory/connectors/email_client.py` | `EmailClient.fetch_recent` | 90-111 | async method | Fetch recent emails from the specified folder. |
| `memory/connectors/email_client.py` | `EmailClient.fetch_by_uid` | 113-120 | async method | Fetch a single email by its IMAP UID. |
| `memory/connectors/email_client.py` | `EmailClient.search` | 122-143 | async method | Search emails by subject or sender. |
| `memory/connectors/email_client.py` | `EmailClient.list_folders` | 145-150 | async method | List available IMAP folders. |
| `memory/connectors/email_client.py` | `EmailClient.send` | 152-175 | async method | Send an email via SMTP. |
| `memory/connectors/email_client.py` | `EmailClient._quote_folder` | 178-182 | method | Quote IMAP folder name if it contains special characters. |
| `memory/connectors/email_client.py` | `EmailClient._test_imap` | 186-209 | method | Test IMAP connection (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._fetch_imap` | 211-254 | method | Fetch recent emails via IMAP (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._fetch_single` | 256-281 | method | Fetch a single email by UID (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._search_imap` | 283-327 | method | Search emails via IMAP (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._connect` | 329-336 | method | Create and authenticate an IMAP connection (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._fetch_uids_since_uid` | 338-353 | method | Return UIDs strictly greater than last_uid (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._fetch_uids_since_date` | 355-370 | method | Return UIDs from emails in the last N days (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._list_folders` | 372-397 | method | List IMAP folders (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._send_smtp` | 399-421 | method | Send an email via SMTP (blocking). |
| `memory/connectors/email_client.py` | `EmailClient._fetch_and_parse` | 425-446 | method | Fetch and parse a single email by UID from an open connection. |
| `memory/connectors/email_client.py` | `EmailClient._parse_message` | 448-544 | method | Parse a stdlib email.message.Message into our EmailMessage model. |
| `memory/connectors/email_client.py` | `EmailClient._decode_header` | 547-561 | method | Decode RFC 2047 encoded header values. |
| `memory/connectors/email_connector.py` | `_format_email_for_extraction` | 26-42 | function | Format a single email into a Librarian-style transcript. |
| `memory/connectors/email_connector.py` | `EmailConnector` | 45-231 | class | Bridges the email inbox with PMS ingestion pipeline. |
| `memory/connectors/email_connector.py` | `EmailConnector.__init__` | 57-68 | method | Method block. |
| `memory/connectors/email_connector.py` | `EmailConnector.get_status` | 70-74 | async method | Check email connection status. |
| `memory/connectors/email_connector.py` | `EmailConnector.fetch_recent` | 76-98 | async method | Fetch recent email summaries (no ingestion). |
| `memory/connectors/email_connector.py` | `EmailConnector.search_emails` | 100-118 | async method | Search emails by subject or sender. |
| `memory/connectors/email_connector.py` | `EmailConnector.get_email` | 120-139 | async method | Fetch a single email with full content. |
| `memory/connectors/email_connector.py` | `EmailConnector.ingest_email` | 141-227 | async method | Ingest a specific email into PMS through the Librarian. |
| `memory/connectors/email_connector.py` | `EmailConnector.list_folders` | 229-231 | async method | List available email folders. |
| `memory/current_situation.py` | `Geofence` | 30-60 | class | A known user-world place represented by a circular geofence. |
| `memory/current_situation.py` | `Geofence.from_mapping` | 41-60 | method | Method block. |
| `memory/current_situation.py` | `_dotenv_values` | 63-83 | function | Function block. |
| `memory/current_situation.py` | `_env_first` | 86-96 | function | Function block. |
| `memory/current_situation.py` | `_env_bool` | 99-103 | function | Function block. |
| `memory/current_situation.py` | `current_situation_path` | 106-108 | function | Function block. |
| `memory/current_situation.py` | `location_update_token` | 111-112 | function | Function block. |
| `memory/current_situation.py` | `geofence_path` | 115-117 | function | Function block. |
| `memory/current_situation.py` | `stale_after_seconds` | 120-128 | function | Function block. |
| `memory/current_situation.py` | `_utc_now` | 131-132 | function | Function block. |
| `memory/current_situation.py` | `_iso_z` | 135-136 | function | Function block. |
| `memory/current_situation.py` | `_parse_datetime` | 139-151 | function | Function block. |
| `memory/current_situation.py` | `haversine_m` | 154-164 | function | Function block. |
| `memory/current_situation.py` | `load_geofences` | 167-184 | function | Function block. |
| `memory/current_situation.py` | `_nearest_geofence` | 187-204 | function | Function block. |
| `memory/current_situation.py` | `_accuracy_score` | 207-218 | function | Function block. |
| `memory/current_situation.py` | `_freshness_score` | 221-230 | function | Function block. |
| `memory/current_situation.py` | `_place_score` | 233-246 | function | Function block. |
| `memory/current_situation.py` | `_validate_coordinates` | 249-253 | function | Function block. |
| `memory/current_situation.py` | `reverse_geocode` | 256-299 | function | Return a compact Google Maps reverse-geocode result when enabled. |
| `memory/current_situation.py` | `_build_location` | 302-365 | function | Function block. |
| `memory/current_situation.py` | `_default_state` | 368-382 | function | Function block. |
| `memory/current_situation.py` | `_write_json_atomic` | 385-389 | function | Function block. |
| `memory/current_situation.py` | `update_current_location` | 392-406 | function | Function block. |
| `memory/current_situation.py` | `_refresh_location` | 409-431 | function | Function block. |
| `memory/current_situation.py` | `redact_state` | 434-444 | function | Return a prompt-safe/current-situation view without raw GPS. |
| `memory/current_situation.py` | `read_current_situation` | 447-459 | function | Function block. |
| `memory/db/connection.py` | `_reject_c_drive_legacy_db` | 11-29 | function | Prevent live C-drive runtime from silently reopening legacy PMS stores. |
| `memory/db/connection.py` | `get_connection` | 32-40 | async function | Open a configured aiosqlite connection with WAL mode and foreign keys. |
| `memory/db/connection.py` | `DatabaseManager` | 43-79 | class | Manages a persistent connection for the application lifetime. |
| `memory/db/connection.py` | `DatabaseManager.__init__` | 46-48 | method | Method block. |
| `memory/db/connection.py` | `DatabaseManager.connect` | 50-54 | async method | Open the persistent connection. |
| `memory/db/connection.py` | `DatabaseManager.disconnect` | 56-60 | async method | Close the persistent connection. |
| `memory/db/connection.py` | `DatabaseManager.conn` | 63-67 | method | Return the active connection. |
| `memory/db/connection.py` | `DatabaseManager.transaction` | 70-79 | async method | Execute operations within an explicit transaction. |
| `memory/db/migrations.py` | `get_current_version` | 30-40 | async function | Return the highest applied schema version, or 0 if none. |
| `memory/db/migrations.py` | `discover_migrations` | 43-59 | function | Scan the migrations directory and return (version, filepath) pairs sorted by version. |
| `memory/db/migrations.py` | `run_migrations` | 62-112 | async function | Apply all pending migrations and return a list of applied version numbers. |
| `memory/db/operations.py` | `_contact_exists` | 36-45 | async function | Check if a contact with the same name (case-insensitive) already exists. |
| `memory/db/operations.py` | `_title_exists` | 59-71 | async function | Check if an active record with the same title/summary already exists. |
| `memory/db/operations.py` | `insert_record` | 74-148 | async function | Insert a new record into a table. |
| `memory/db/operations.py` | `_safe_embed` | 151-156 | async function | Call the embed hook, swallowing any exception so writes are never blocked. |
| `memory/db/operations.py` | `update_record` | 161-189 | async function | Update fields on an existing record. |
| `memory/feedback.py` | `normalize_participant_id` | 129-134 | function | Return the stable participant key used for feedback attribution. |
| `memory/feedback.py` | `reaction_source_id` | 137-140 | function | Build the deterministic source id for one reaction toggle. |
| `memory/feedback.py` | `reaction_signal` | 143-151 | function | Map a reaction emoji to normalized signal and base strength. |
| `memory/feedback.py` | `classify_language_feedback` | 154-171 | function | Classify explicit Marc feedback phrasing when attribution is clear. |
| `memory/feedback.py` | `_infer_contribution_type` | 174-184 | function | Function block. |
| `memory/feedback.py` | `normalize_reaction_feedback_event` | 187-250 | function | Normalize one chatroom reaction into a feedback_events row payload. |
| `memory/feedback.py` | `normalize_language_feedback_event` | 253-295 | function | Normalize clear natural-language feedback into a feedback_events row. |
| `memory/feedback.py` | `_actor_label` | 298-299 | function | Function block. |
| `memory/feedback.py` | `reaction_runtime_feedback_payload` | 302-357 | function | Return the compact runtime payload sent to the authoring CC. |
| `memory/feedback.py` | `language_runtime_feedback_payload` | 360-407 | function | Return compact runtime payload for natural-language feedback. |
| `memory/feedback.py` | `build_session_calibration` | 410-469 | function | Summarize recent active feedback into short-lived style weights. |
| `memory/feedback.py` | `upsert_reaction_feedback_event` | 472-540 | async function | Persist the normalized feedback event for a chatroom reaction. |
| `memory/feedback.py` | `upsert_language_feedback_event` | 543-607 | async function | Persist a normalized natural-language feedback event. |
| `memory/feedback_preferences.py` | `_metadata` | 14-24 | function | Function block. |
| `memory/feedback_preferences.py` | `_event_text` | 27-34 | function | Function block. |
| `memory/feedback_preferences.py` | `_cluster_for_event` | 37-76 | function | Function block. |
| `memory/feedback_preferences.py` | `_threshold_reason` | 79-103 | function | Function block. |
| `memory/feedback_preferences.py` | `_confidence` | 106-111 | function | Function block. |
| `memory/feedback_preferences.py` | `synthesize_preference_candidates` | 114-179 | function | Return candidate preference payloads from active feedback events. |
| `memory/feedback_preferences.py` | `fetch_feedback_events` | 182-208 | async function | Async function block. |
| `memory/feedback_preferences.py` | `upsert_feedback_preference` | 211-250 | async function | Async function block. |
| `memory/feedback_preferences.py` | `synthesize_feedback_preferences` | 253-273 | async function | Async function block. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline` | 36-186 | class | Direct-write pipeline — all writes approved, logged for the chronological record. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline.__init__` | 47-61 | method | Method block. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline.set_escalation_hook` | 63-65 | method | No-op — governance is gone, nothing escalates. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline.submit_change` | 67-97 | async method | Log the change, return approved. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline.submit_change_and_wait` | 99-119 | async method | Same as submit_change — nothing blocks anymore. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline._log_decision` | 121-159 | async method | Write a decision to the change_log table — the chronological record. |
| `memory/governance/approval_pipeline.py` | `ApprovalPipeline.get_change_log` | 161-186 | async method | Query the change_log with optional filters — the chronological record. |
| `memory/governance/change_log_review.py` | `ChangeLogReviewError` | 97-98 | class | Raised when a pending proposal cannot be reviewed or applied. |
| `memory/governance/change_log_review.py` | `parse_proposed_change` | 101-111 | function | Best-effort JSON parser for `change_log.proposed_change`. |
| `memory/governance/change_log_review.py` | `_as_json_text` | 114-117 | function | Function block. |
| `memory/governance/change_log_review.py` | `_clean_updates` | 120-131 | function | Function block. |
| `memory/governance/change_log_review.py` | `_normalize_create_record` | 134-175 | function | Adapt extractor-friendly field names to the current table schema. |
| `memory/governance/change_log_review.py` | `_update_record` | 178-192 | async function | Async function block. |
| `memory/governance/change_log_review.py` | `_insert_record` | 195-236 | async function | Async function block. |
| `memory/governance/change_log_review.py` | `_insert_tag_orbits` | 239-278 | async function | Async function block. |
| `memory/governance/change_log_review.py` | `_normalize_user_world_bucket` | 281-285 | function | Function block. |
| `memory/governance/change_log_review.py` | `_normalize_user_world_record` | 288-321 | function | Function block. |
| `memory/governance/change_log_review.py` | `_merge_user_world_record` | 324-341 | function | Function block. |
| `memory/governance/change_log_review.py` | `_ordered_unique` | 344-353 | function | Function block. |
| `memory/governance/change_log_review.py` | `_write_user_world` | 356-360 | function | Function block. |
| `memory/governance/change_log_review.py` | `_upsert_user_world_record` | 363-379 | function | Function block. |
| `memory/governance/change_log_review.py` | `_normalize_tag` | 382-383 | function | Function block. |
| `memory/governance/change_log_review.py` | `_final_decision` | 386-387 | function | Function block. |
| `memory/governance/change_log_review.py` | `apply_approved_change` | 390-487 | async function | Apply an approved change_log proposal to target PMS tables. |
| `memory/governance/change_log_review.py` | `resolve_change_log_entry` | 490-541 | async function | Approve/reject one pending change_log proposal. |
| `memory/governance/change_log_review.py` | `resolve_change_log_entries` | 544-592 | async function | Approve/reject a bounded list of pending change_log proposals. |
| `memory/governance/change_log_review.py` | `_preview_record` | 595-602 | function | Function block. |
| `memory/governance/change_log_review.py` | `_title_for` | 605-616 | function | Function block. |
| `memory/governance/change_log_review.py` | `change_log_review_item` | 619-665 | function | Format one pending change_log row for `/chatroom/governance`. |
| `memory/governance/change_log_review.py` | `correct_change_log_entry` | 668-738 | async function | Reject a proposal but apply Marc's corrected value to the target record. |
| `memory/governance/change_log_writer.py` | `_risk_for` | 35-46 | function | Map chain outcome to a coarse risk bucket. |
| `memory/governance/change_log_writer.py` | `_cost_of_inaction` | 49-54 | function | Function block. |
| `memory/governance/change_log_writer.py` | `_proposed_change_payload` | 57-119 | function | Pack the record + provenance into the `proposed_change` TEXT column. |
| `memory/governance/change_log_writer.py` | `write_extraction_pending` | 122-260 | async function | Write one pending `change_log` row per extracted record. |
| `memory/governance/escalation.py` | `ChainStep` | 75-94 | class | One model's evaluation in the chain. |
| `memory/governance/escalation.py` | `ChainStep.to_dict` | 93-94 | method | Method block. |
| `memory/governance/escalation.py` | `ChainResult` | 98-124 | class | Full trace of one governance decision. |
| `memory/governance/escalation.py` | `ChainResult.total_duration_s` | 110-111 | method | Method block. |
| `memory/governance/escalation.py` | `ChainResult.to_dict` | 113-124 | method | Method block. |
| `memory/governance/escalation.py` | `_project_root` | 129-130 | function | Function block. |
| `memory/governance/escalation.py` | `_load_prompt` | 133-156 | function | Resolve and read the system-prompt file. |
| `memory/governance/escalation.py` | `_coerce_confidence` | 161-170 | function | Function block. |
| `memory/governance/escalation.py` | `thresholds_for_task` | 173-186 | function | Resolve global defaults plus task-local threshold overrides. |
| `memory/governance/escalation.py` | `chain_outcome` | 189-200 | function | Classify a completed chain as accept, escalate, or skip. |
| `memory/governance/escalation.py` | `_step_from_result` | 203-216 | function | Function block. |
| `memory/governance/escalation.py` | `run_one` | 219-290 | async function | Run a single model evaluation. |
| `memory/governance/escalation.py` | `run_chain` | 293-394 | async function | Run the provider-selected highest model once. |
| `memory/governance/extraction.py` | `ExtractionResult` | 33-50 | class | Outcome of one extraction pass over a transcript. |
| `memory/governance/extraction.py` | `ExtractionResult.total_records` | 40-41 | method | Method block. |
| `memory/governance/extraction.py` | `ExtractionResult.confidence` | 44-46 | method | Method block. |
| `memory/governance/extraction.py` | `ExtractionResult.escalated_to_marc` | 49-50 | method | Method block. |
| `memory/governance/extraction.py` | `_normalize_records` | 53-83 | function | Coerce the chain's `decision` output into the canonical per-table dict. |
| `memory/governance/extraction.py` | `extract_records` | 86-136 | async function | Run the extraction chain on a single transcript. |
| `memory/governance/llm_runner.py` | `ProposalResult` | 37-48 | class | One model's output for one row. |
| `memory/governance/llm_runner.py` | `_extract_json` | 54-73 | function | Pull the first JSON object out of an assistant text block. |
| `memory/governance/llm_runner.py` | `_pick_field` | 84-91 | function | Return (value, key_used). |
| `memory/governance/llm_runner.py` | `run_claude_proposal` | 94-227 | async function | Spawn `claude -p` with the given model and return its proposal. |
| `memory/governance/llm_runner.py` | `run_model_proposal` | 230-278 | async function | Async function block. |
| `memory/governance/llm_runner.py` | `_proposal_from_text` | 281-324 | function | Function block. |
| `memory/governance/monitor_stats.py` | `_path` | 36-37 | function | Function block. |
| `memory/governance/monitor_stats.py` | `_read` | 40-47 | function | Function block. |
| `memory/governance/monitor_stats.py` | `_atomic_write` | 50-55 | function | Function block. |
| `memory/governance/monitor_stats.py` | `record_extraction_event` | 58-90 | function | Bump cumulative extraction counters and stamp last-active timestamp. |
| `memory/governance/monitor_stats.py` | `reset_extraction_stats` | 93-99 | function | Wipe cumulative counters. |
| `memory/governance/monitor_stats.py` | `add_chain_tokens` | 102-114 | function | Accumulate chain-step tokens from a ChainResult into a per-run state dict. |
| `memory/governance/tasks.py` | `TaskConfig` | 13-27 | class | Shared per-task config. |
| `memory/governance/tasks.py` | `get` | 43-48 | function | Look up a task config by name; raise ValueError if unknown. |
| `memory/mcp/ai_tools.py` | `AIToolHandlers` | 7-14 | class | No-op stub. |
| `memory/mcp/ai_tools.py` | `AIToolHandlers.__init__` | 10-11 | method | Method block. |
| `memory/mcp/ai_tools.py` | `AIToolHandlers.handle_ai_check` | 13-14 | async method | Async method block. |
| `memory/mcp/file_write_handler.py` | `_preview` | 12-16 | function | Function block. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler` | 19-185 | class | Runs protected file writes through the blocking governance pipeline. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler.__init__` | 22-24 | method | Method block. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler._resolve` | 26-31 | method | Method block. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler._reason` | 33-39 | method | Method block. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler.governed_write` | 41-103 | async method | Async method block. |
| `memory/mcp/file_write_handler.py` | `GovernedFileWriteHandler.governed_edit` | 105-185 | async method | Async method block. |
| `memory/mcp/handlers.py` | `MCPToolHandler` | 236-616 | class | Transport-agnostic handler for MCP tools. |
| `memory/mcp/handlers.py` | `MCPToolHandler.__init__` | 243-260 | method | Method block. |
| `memory/mcp/handlers.py` | `MCPToolHandler.handle_tool_call` | 262-291 | async method | Dispatch a tool call to the appropriate handler. |
| `memory/mcp/handlers.py` | `MCPToolHandler._disabled_in_v2_primary` | 293-298 | method | Method block. |
| `memory/mcp/handlers.py` | `MCPToolHandler._requires_conn` | 300-303 | method | Method block. |
| `memory/mcp/handlers.py` | `MCPToolHandler._requires_pipeline` | 305-308 | method | Method block. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_memory_query` | 310-323 | async method | memory_query: Natural language query with six-layer retrieval. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_memory_store` | 325-357 | async method | memory_store: Create new entry through governance. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_memory_update` | 359-399 | async method | memory_update: Modify entry through governance. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_memory_search` | 401-416 | async method | memory_search: Full-text search. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_ai_log` | 418-420 | async method | ai_log: removed — ai_reasoning table deprecated 2026-04-26. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_ai_check` | 422-424 | async method | ai_check: Delegate to AIToolHandlers. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_escalation_respond` | 426-448 | async method | escalation_respond: Deprecated — governance was removed. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_thinker_analyze` | 450-487 | async method | thinker_analyze: Run a Thinker analysis pass. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_conversation_search` | 489-554 | async method | conversation_search: Search raw conversation archives. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_governed_write` | 556-566 | async method | governed_write: Block on Executive approval, then write a protected file. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_governed_edit` | 568-578 | async method | governed_edit: Block on Executive approval, then edit a protected file. |
| `memory/mcp/handlers.py` | `MCPToolHandler._tool_ui_highlight` | 580-616 | async method | ui_highlight: ask the active chatroom browser to point at a UI feature. |
| `memory/mcp/handlers.py` | `_normalize_feature_id` | 619-626 | function | Function block. |
| `memory/mcp/handlers.py` | `_normalize_duration_ms` | 629-634 | function | Function block. |
| `memory/mcp/protected_paths.py` | `_resolve_project_root` | 27-28 | function | Function block. |
| `memory/mcp/protected_paths.py` | `normalize_path` | 31-47 | function | Function block. |
| `memory/mcp/protected_paths.py` | `_is_under` | 50-57 | function | Function block. |
| `memory/mcp/protected_paths.py` | `_is_self_protecting_path` | 70-80 | function | These stay blocked even under an active claim lease -- editing them can permanently disable the guard itself, not just change prompt wording. |
| `memory/mcp/protected_paths.py` | `protected_path_reason` | 83-158 | function | `has_active_claim_lease=True` lifts the block for any protected path EXCEPT the guard's own self-protecting files (see `_is_self_protecting_path`). |
| `memory/mcp/protected_paths.py` | `is_protected_path` | 161-178 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_official_model_id` | 39-43 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_effort_args_for_model` | 46-50 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner` | 53-311 | class | Run backend model calls through `claude -p`. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.__init__` | 62-74 | method | Method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.generate_text` | 76-103 | async method | Async method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.generate_json` | 105-146 | async method | Async method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.classify` | 148-181 | async method | Async method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.generate_with_thinking` | 183-218 | async method | Run a deep reasoning call through the CLI runner. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner.run_agent` | 220-276 | async method | Async method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner._model_for_tier` | 278-282 | method | Method block. |
| `memory/model_runner/claude_cli.py` | `ClaudeCliModelRunner._invoke` | 284-311 | async method | Async method block. |
| `memory/model_runner/claude_cli.py` | `_run_command` | 314-318 | async function | Async function block. |
| `memory/model_runner/claude_cli.py` | `_run_streaming_command` | 321-340 | async function | Async function block. |
| `memory/model_runner/claude_cli.py` | `_maybe_await` | 343-345 | async function | Async function block. |
| `memory/model_runner/claude_cli.py` | `_parse_claude_stream` | 348-370 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_json_instruction` | 373-378 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_repair_instruction` | 381-388 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_sha256` | 391-392 | function | Function block. |
| `memory/model_runner/claude_cli.py` | `_elapsed_ms` | 395-396 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner` | 51-351 | class | Run backend model calls through `codex exec --json`. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.__init__` | 61-78 | method | Method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.generate_text` | 80-109 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.generate_json` | 111-154 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.classify` | 156-189 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.generate_with_thinking` | 191-222 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner.run_agent` | 224-299 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner._model_for_tier` | 301-305 | method | Method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner._reasoning_for_tier` | 307-311 | method | Method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner._reasoning_for_budget` | 313-318 | method | Method block. |
| `memory/model_runner/codex_cli.py` | `CodexCliModelRunner._invoke` | 320-351 | async method | Async method block. |
| `memory/model_runner/codex_cli.py` | `_run_command` | 354-358 | async function | Async function block. |
| `memory/model_runner/codex_cli.py` | `_run_streaming_command` | 361-380 | async function | Async function block. |
| `memory/model_runner/codex_cli.py` | `_maybe_await` | 383-385 | async function | Async function block. |
| `memory/model_runner/codex_cli.py` | `find_codex_command` | 388-401 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_parse_codex_stream` | 404-424 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_format_codex_agent_empty_output` | 427-452 | function | Build a bounded diagnostic for returncode-0 agent runs with no text. |
| `memory/model_runner/codex_cli.py` | `_codex_stream_types` | 455-465 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_redacted_command` | 468-471 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_codex_env_summary` | 474-485 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_diagnostic_tail` | 488-492 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_extract_agent_text` | 495-510 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_normalize_usage` | 513-519 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_combined_prompt` | 522-525 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_json_instruction` | 528-533 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_repair_instruction` | 536-543 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_sha256` | 546-547 | function | Function block. |
| `memory/model_runner/codex_cli.py` | `_elapsed_ms` | 550-551 | function | Function block. |
| `memory/model_runner/factory.py` | `selected_backend_provider` | 13-23 | function | Return the install-level backend provider. |
| `memory/model_runner/factory.py` | `create_model_runner` | 26-34 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner` | 57-369 | class | Run backend model calls through `grok -p` (single-turn headless). |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.__init__` | 67-84 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.generate_text` | 86-115 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.generate_json` | 117-160 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.classify` | 162-195 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.generate_with_thinking` | 197-228 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner.run_agent` | 230-280 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._model_for_tier` | 282-286 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._reasoning_for_tier` | 288-292 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._reasoning_for_budget` | 294-299 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._build_cmd` | 301-326 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._invoke` | 328-344 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `GrokCliModelRunner._invoke_parts` | 346-369 | async method | Async method block. |
| `memory/model_runner/grok_cli.py` | `_prompt_file` | 372-399 | class | Context manager that writes prompt text to a tempfile for --prompt-file. |
| `memory/model_runner/grok_cli.py` | `_prompt_file.__init__` | 375-377 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `_prompt_file.__enter__` | 379-392 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `_prompt_file.__exit__` | 394-399 | method | Method block. |
| `memory/model_runner/grok_cli.py` | `_run_command` | 402-408 | async function | Async function block. |
| `memory/model_runner/grok_cli.py` | `_run_streaming_command` | 411-432 | async function | Async function block. |
| `memory/model_runner/grok_cli.py` | `_maybe_await` | 435-437 | async function | Async function block. |
| `memory/model_runner/grok_cli.py` | `find_grok_command` | 440-457 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_parse_grok_stream` | 460-462 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_parse_grok_stream_parts` | 465-500 | function | Parse Grok streaming-json output. |
| `memory/model_runner/grok_cli.py` | `_normalize_usage` | 503-509 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_combined_prompt` | 512-515 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_json_instruction` | 518-523 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_repair_instruction` | 526-533 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_sha256` | 536-537 | function | Function block. |
| `memory/model_runner/grok_cli.py` | `_elapsed_ms` | 540-541 | function | Function block. |
| `memory/model_runner/json_contract.py` | `extract_json_object` | 13-29 | function | Extract the first JSON object from plain text or a fenced block. |
| `memory/model_runner/json_contract.py` | `validate_json_schema` | 32-40 | function | Validate the small JSON Schema subset backend workers need now. |
| `memory/model_runner/json_contract.py` | `_validate` | 43-65 | function | Function block. |
| `memory/model_runner/json_contract.py` | `_type_matches` | 68-85 | function | Function block. |
| `memory/model_runner/subprocess_bridge.py` | `ProcessHandle` | 40-69 | class | Loop-agnostic stand-in for asyncio.subprocess.Process. |
| `memory/model_runner/subprocess_bridge.py` | `ProcessHandle.__init__` | 48-52 | method | Method block. |
| `memory/model_runner/subprocess_bridge.py` | `ProcessHandle.terminate` | 54-58 | method | Method block. |
| `memory/model_runner/subprocess_bridge.py` | `ProcessHandle.wait` | 60-65 | async method | Async method block. |
| `memory/model_runner/subprocess_bridge.py` | `ProcessHandle._mark_done` | 67-69 | method | Method block. |
| `memory/model_runner/subprocess_bridge.py` | `_ensure_bridge_loop` | 77-107 | function | Function block. |
| `memory/model_runner/subprocess_bridge.py` | `_call_on_loop` | 110-119 | async function | Run func(arg) on loop (a different thread's loop) and await completion. |
| `memory/model_runner/subprocess_bridge.py` | `run_streaming_agent` | 122-255 | async function | Spawn cmd on the Proactor bridge thread; await the result from any caller loop. |
| `memory/model_runner/types.py` | `ModelRunnerError` | 12-13 | class | Base error for backend model execution failures. |
| `memory/model_runner/types.py` | `ModelRunnerValidationError` | 16-17 | class | Raised when a model result cannot satisfy the requested schema. |
| `memory/model_runner/types.py` | `TextResult` | 21-30 | class | Class block. |
| `memory/model_runner/types.py` | `JsonResult` | 34-43 | class | Class block. |
| `memory/model_runner/types.py` | `ClassifyResult` | 47-56 | class | Class block. |
| `memory/model_runner/types.py` | `ThinkingResult` | 60-69 | class | Class block. |
| `memory/model_runner/types.py` | `AgentRunResult` | 73-83 | class | Class block. |
| `memory/model_runner/types.py` | `ModelRunner` | 90-152 | class | Class block. |
| `memory/model_runner/types.py` | `ModelRunner.generate_text` | 91-101 | async method | Async method block. |
| `memory/model_runner/types.py` | `ModelRunner.generate_json` | 103-114 | async method | Async method block. |
| `memory/model_runner/types.py` | `ModelRunner.classify` | 116-125 | async method | Async method block. |
| `memory/model_runner/types.py` | `ModelRunner.generate_with_thinking` | 127-138 | async method | Async method block. |
| `memory/model_runner/types.py` | `ModelRunner.run_agent` | 140-152 | async method | Async method block. |
| `memory/models/ai_profile.py` | `AIProfile` | 17-83 | class | An AI model family profile with tracked expertise and accuracy. |
| `memory/models/ai_profile.py` | `AIProfile.accuracy_rate` | 53-58 | method | Fraction of claims that were validated vs contradicted. |
| `memory/models/ai_profile.py` | `AIProfile.agreement_rate` | 61-66 | method | How often this family agrees with other families. |
| `memory/models/ai_profile.py` | `AIProfile.to_summary` | 68-83 | method | Human-readable summary for API display. |
| `memory/models/base.py` | `LifecycleStatus` | 13-18 | class | Class block. |
| `memory/models/base.py` | `generate_uuid` | 21-22 | function | Function block. |
| `memory/models/base.py` | `now_iso` | 25-26 | function | Function block. |
| `memory/models/base.py` | `MemoryBase` | 29-80 | class | Universal fields present on every memory record (spec Section 3.1). |
| `memory/models/base.py` | `MemoryBase.parse_preserved` | 45-51 | method | Accept preserved as SQLite integer (0/1) or Python bool. |
| `memory/models/base.py` | `MemoryBase.parse_tags` | 55-67 | method | Accept tags as JSON string (from SQLite) or list. |
| `memory/models/base.py` | `MemoryBase.serialize_tags` | 70-72 | method | Serialize tags to JSON string for SQLite storage. |
| `memory/models/base.py` | `MemoryBase.from_row` | 75-80 | method | Hydrate a model instance from an aiosqlite Row. |
| `memory/models/base.py` | `MemoryCreate` | 83-101 | class | Base for creation models — no id/timestamps, those are auto-generated. |
| `memory/models/base.py` | `MemoryCreate.parse_tags` | 90-101 | method | Method block. |
| `memory/models/base.py` | `MemoryUpdate` | 104-126 | class | Base for update models — all fields optional. |
| `memory/models/base.py` | `MemoryUpdate.parse_tags` | 115-126 | method | Method block. |
| `memory/models/change_log.py` | `Operation` | 12-16 | class | Class block. |
| `memory/models/change_log.py` | `ExecutiveDecision` | 19-21 | class | Class block. |
| `memory/models/change_log.py` | `ChangeLogEntry` | 24-47 | class | Full change_log record. |
| `memory/models/change_log.py` | `ChangeLogEntry.from_row` | 43-47 | method | Method block. |
| `memory/models/contact.py` | `Contact` | 9-16 | class | Full contact record as stored in the database. |
| `memory/models/contact.py` | `ContactCreate` | 19-26 | class | Input model for creating a new contact. |
| `memory/models/contact.py` | `ContactUpdate` | 29-36 | class | Input model for updating a contact. |
| `memory/models/decision.py` | `DecisionStatus` | 13-16 | class | Class block. |
| `memory/models/decision.py` | `Decision` | 19-42 | class | Full decision record as stored in the database. |
| `memory/models/decision.py` | `Decision.parse_alternatives` | 31-42 | method | Method block. |
| `memory/models/decision.py` | `DecisionCreate` | 45-68 | class | Input model for creating a new decision. |
| `memory/models/decision.py` | `DecisionCreate.parse_alternatives` | 57-68 | method | Method block. |
| `memory/models/decision.py` | `DecisionUpdate` | 71-79 | class | Input model for updating a decision. |
| `memory/models/governance.py` | `ChangeRequest` | 10-23 | class | A proposed change submitted by the Thinker to the Librarian. |
| `memory/models/governance.py` | `GovernanceDecision` | 26-40 | class | The Librarian's response to a change request. |
| `memory/models/governance.py` | `EscalationResolution` | 43-47 | class | Executive's resolution of an escalated change request. |
| `memory/models/idea.py` | `IdeaStatus` | 12-17 | class | Class block. |
| `memory/models/idea.py` | `Idea` | 20-28 | class | Full idea record as stored in the database. |
| `memory/models/idea.py` | `IdeaCreate` | 31-38 | class | Input model for creating a new idea. |
| `memory/models/idea.py` | `IdeaUpdate` | 41-48 | class | Input model for updating an idea. |
| `memory/models/monitor.py` | `SubprocessState` | 10-15 | class | Class block. |
| `memory/models/monitor.py` | `SubprocessInfo` | 19-38 | class | Class block. |
| `memory/models/monitor.py` | `MonitorSnapshot` | 42-48 | class | Class block. |
| `memory/models/project.py` | `ProjectStatus` | 10-14 | class | Class block. |
| `memory/models/project.py` | `Project` | 17-22 | class | Full project record as stored in the database. |
| `memory/models/project.py` | `ProjectCreate` | 25-30 | class | Input model for creating a new project. |
| `memory/models/project.py` | `ProjectUpdate` | 33-38 | class | Input model for updating a project. |
| `memory/monitor/app.py` | `index` | 34-35 | async function | Async function block. |
| `memory/monitor/app.py` | `health` | 39-40 | async function | Async function block. |
| `memory/retrieval/context_assembler.py` | `ContextLayer` | 28-34 | class | A single layer's contribution to the context package. |
| `memory/retrieval/context_assembler.py` | `ContextPackage` | 37-69 | class | Structured retrieval package returned to the Thinker. |
| `memory/retrieval/context_assembler.py` | `ContextPackage.to_summary` | 55-69 | method | Return a condensed summary suitable for the Thinker's context window. |
| `memory/retrieval/context_assembler.py` | `_condense_record` | 72-84 | function | Strip internal metadata, keep content fields for the Thinker. |
| `memory/retrieval/context_assembler.py` | `RetrievalEngine` | 87-220 | class | Orchestrates all 6 retrieval layers into a structured context package. |
| `memory/retrieval/context_assembler.py` | `RetrievalEngine.__init__` | 101-103 | method | Method block. |
| `memory/retrieval/context_assembler.py` | `RetrievalEngine.query` | 105-195 | async method | Execute full six-layer retrieval and assemble context package. |
| `memory/retrieval/context_assembler.py` | `RetrievalEngine._update_reference_timestamps` | 197-220 | async method | Update last_referenced_at for all records that were returned in a query. |
| `memory/retrieval/direct_match.py` | `sanitize_fts_query` | 31-37 | function | Sanitize a query string for safe FTS5 MATCH usage. |
| `memory/retrieval/direct_match.py` | `search_canonical_fts` | 43-45 | async function | Stub — PMS v2 canonical search removed. |
| `memory/retrieval/direct_match.py` | `search_fts` | 48-112 | async function | Search across legacy FTS tables by default. |
| `memory/retrieval/inverse_relevance.py` | `InverseRelevanceProvider` | 24-36 | class | Abstract base for inverse relevance implementations. |
| `memory/retrieval/inverse_relevance.py` | `InverseRelevanceProvider.find_inverse` | 28-36 | async method | Find records with low topical but high structural overlap. |
| `memory/retrieval/inverse_relevance.py` | `StructuralInverseRelevance` | 39-130 | class | Phase 1 implementation: structural tag matching with topical exclusion. |
| `memory/retrieval/inverse_relevance.py` | `StructuralInverseRelevance.__init__` | 54-55 | method | Method block. |
| `memory/retrieval/inverse_relevance.py` | `StructuralInverseRelevance._classify_tags` | 57-66 | method | Separate tags into structural and topical categories. |
| `memory/retrieval/inverse_relevance.py` | `StructuralInverseRelevance.find_inverse` | 68-130 | async method | Find records sharing structural tags but not topical tags. |
| `memory/retrieval/tag_expansion.py` | `expand_by_tags` | 24-82 | async function | Find records across all tables sharing tags with seed results. |
| `memory/retrieval/tag_expansion.py` | `extract_tags_from_results` | 85-98 | function | Extract all unique tags from a set of results for use in expansion. |
| `memory/retrieval/temporal_proximity.py` | `find_temporal_neighbors` | 25-87 | async function | Find records created or modified within a time window of reference timestamps. |
| `memory/retrieval/temporal_proximity.py` | `extract_timestamps` | 90-97 | function | Extract created_at timestamps from a set of results. |
| `memory/services/autonomous_monitor.py` | `AutonomousMonitor` | 20-80 | class | Creates manual task suggestions and sends task notifications. |
| `memory/services/autonomous_monitor.py` | `AutonomousMonitor.__init__` | 23-31 | method | Method block. |
| `memory/services/autonomous_monitor.py` | `AutonomousMonitor.suggest_manual` | 33-55 | async method | Create a manual task suggestion. |
| `memory/services/autonomous_monitor.py` | `AutonomousMonitor._notify_task_suggestion` | 57-80 | async method | Send a task suggestion to the governance tab for approval. |
| `memory/services/autonomous_tasks.py` | `TaskStatus` | 22-30 | class | Class block. |
| `memory/services/autonomous_tasks.py` | `TaskPriority` | 33-37 | class | Class block. |
| `memory/services/autonomous_tasks.py` | `TaskSource` | 40-47 | class | Class block. |
| `memory/services/autonomous_tasks.py` | `AutonomousTask` | 50-78 | class | A task suggested manually or delegated by another agent. |
| `memory/services/autonomous_tasks.py` | `_row_to_task` | 89-99 | function | Convert a DB row to an AutonomousTask. |
| `memory/services/autonomous_tasks.py` | `TaskQueue` | 102-296 | class | SQLite-backed task queue. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.__init__` | 105-106 | method | Method block. |
| `memory/services/autonomous_tasks.py` | `TaskQueue._execute` | 108-111 | async method | Async method block. |
| `memory/services/autonomous_tasks.py` | `TaskQueue._fetch_one` | 113-118 | async method | Async method block. |
| `memory/services/autonomous_tasks.py` | `TaskQueue._fetch_by_status` | 120-126 | async method | Async method block. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.delegate` | 128-167 | async method | CC-to-CC delegation creates task directly in approved state. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.suggest` | 169-198 | async method | Add a new task suggestion to the queue. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.approve` | 200-213 | async method | Executive approves a suggested task. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.reject` | 215-229 | async method | Executive rejects a suggested task. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.claim` | 231-245 | async method | Agent claims an approved task. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.complete` | 247-261 | async method | Mark a task as completed. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.get` | 263-265 | async method | Get a single task by ID. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.get_approved` | 267-271 | async method | Get approved tasks waiting for pickup. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.get_suggested` | 273-275 | async method | Get tasks awaiting Executive approval. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.get_in_progress` | 277-279 | async method | Get tasks currently being worked on. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.list_all` | 281-287 | async method | List all tasks, optionally filtered by status. |
| `memory/services/autonomous_tasks.py` | `TaskQueue.get_stats` | 289-296 | async method | Summary statistics for the task queue. |
| `memory/services/claude_client.py` | `CreditExhaustedError` | 23-25 | class | Raised when the Anthropic account has no remaining credits. |
| `memory/services/claude_client.py` | `ClaudeClient` | 28-256 | class | Async client for the Anthropic Claude API. |
| `memory/services/claude_client.py` | `ClaudeClient.__init__` | 35-46 | method | Method block. |
| `memory/services/claude_client.py` | `ClaudeClient._get_client` | 48-58 | async method | Async method block. |
| `memory/services/claude_client.py` | `ClaudeClient.generate` | 60-126 | async method | Send a prompt to Claude and return the response text. |
| `memory/services/claude_client.py` | `ClaudeClient.generate_with_thinking` | 128-207 | async method | Send a prompt to Claude with extended thinking enabled. |
| `memory/services/claude_client.py` | `ClaudeClient.ping` | 209-230 | async method | Check if Claude API is reachable and the API key is valid. |
| `memory/services/claude_client.py` | `ClaudeClient.is_available` | 233-242 | method | Whether Claude was reachable on last attempt. |
| `memory/services/claude_client.py` | `ClaudeClient.close` | 244-248 | async method | Close the HTTP client. |
| `memory/services/claude_client.py` | `ClaudeClient._extract_text` | 251-256 | method | Extract text content from Claude API response. |
| `memory/services/durable_monitor_stats.py` | `now_iso` | 17-18 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `_normalize_room_id` | 21-27 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `monitor_stats_path` | 30-36 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `read_monitor_stats` | 39-43 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `write_monitor_stats` | 46-51 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `thinker_stats_filename` | 54-58 | function | Function block. |
| `memory/services/durable_monitor_stats.py` | `record_thinker_event` | 61-148 | function | Update cumulative Thinker monitor state for one participant. |
| `memory/services/llm_client.py` | `LLMClient` | 24-172 | class | Backward-compatible async LLM client backed by model_runner. |
| `memory/services/llm_client.py` | `LLMClient.__new__` | 29-33 | method | Method block. |
| `memory/services/llm_client.py` | `LLMClient.__init__` | 35-65 | method | Method block. |
| `memory/services/llm_client.py` | `LLMClient._proxy_generate` | 67-90 | async method | Async method block. |
| `memory/services/llm_client.py` | `LLMClient.generate` | 92-131 | async method | Run a legacy LLMClient request through the configured provider. |
| `memory/services/llm_client.py` | `LLMClient.ping` | 133-139 | async method | Async method block. |
| `memory/services/llm_client.py` | `LLMClient.close` | 141-144 | async method | Async method block. |
| `memory/services/llm_client.py` | `LLMClient._write_monitor_stats` | 146-172 | method | Write legacy monitor stats for surfaces that still read this file. |
| `memory/services/query_synthesizer.py` | `Citation` | 25-30 | class | A reference to a specific memory record used in the answer. |
| `memory/services/query_synthesizer.py` | `SynthesizedAnswer` | 33-45 | class | Structured answer produced by the query synthesis service. |
| `memory/services/query_synthesizer.py` | `QuerySynthesizer` | 48-226 | class | Synthesizes structured answers from memory retrieval results. |
| `memory/services/query_synthesizer.py` | `QuerySynthesizer.__init__` | 59-63 | method | Method block. |
| `memory/services/query_synthesizer.py` | `QuerySynthesizer.synthesize` | 65-138 | async method | Synthesize a structured answer to a natural language question. |
| `memory/services/query_synthesizer.py` | `QuerySynthesizer._format_context` | 140-186 | method | Format a ContextPackage into LLM-readable text with record IDs. |
| `memory/services/query_synthesizer.py` | `QuerySynthesizer._parse_response` | 188-226 | method | Parse the LLM's JSON response, with fallback for malformed output. |
| `memory/services/reasoning_loop.py` | `ReasoningResult` | 36-71 | class | Output of a reasoning loop run. |
| `memory/services/reasoning_loop.py` | `ReasoningResult.to_dict` | 54-71 | method | Method block. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop` | 115-492 | class | Executes the GATHER→REASON→STRUCTURE→STORE pipeline for a thinker session. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop.__init__` | 118-136 | method | Method block. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop.run` | 138-224 | async method | Execute the full reasoning loop for a session. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._gather` | 230-265 | async method | Pull context from PMS (6-layer retrieval) and conversation archives. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._search_archives` | 267-287 | async method | Search conversation archives via FTS5. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._format_context` | 289-334 | method | Format gathered context into a text block for the model. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._reason` | 340-364 | async method | Run the reasoning model. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._structure` | 370-406 | async method | Parse raw reasoning output into structured fields. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._try_parse_json` | 408-431 | method | Try to parse JSON from text, handling common edge cases. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._store` | 437-480 | async method | Update session with results and post to thinker tab. |
| `memory/services/reasoning_loop.py` | `ReasoningLoop._post_to_session` | 486-492 | async method | Post a progress message to the session's thinker tab thread. |
| `memory/services/room_config.py` | `_config_path` | 40-45 | function | Function block. |
| `memory/services/room_config.py` | `_seed_defaults` | 48-57 | function | Function block. |
| `memory/services/room_config.py` | `_load_file` | 60-78 | function | Function block. |
| `memory/services/room_config.py` | `reset_cache` | 81-84 | function | Drop the cached file read (tests / after an installer restamp). |
| `memory/services/room_config.py` | `home_room_id` | 87-90 | function | The permanent home room id for this install (env > file > default). |
| `memory/services/room_config.py` | `workshop_room_id` | 93-96 | function | The permanent Workshop room id for this install (env > file > default). |
| `memory/services/room_config.py` | `permanent_room_ids` | 99-101 | function | The two rooms that cannot be deleted, archived, or renamed. |
| `memory/services/room_config.py` | `room_config` | 104-106 | function | Resolved config for callers (API/browser): the two live ids. |
| `memory/services/scheduler.py` | `MaintenanceScheduler` | 45-738 | class | Manages background asyncio loops for Thinker sessions. |
| `memory/services/scheduler.py` | `MaintenanceScheduler.__init__` | 48-73 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._loadavg` | 77-81 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler.start` | 83-102 | method | Start both background loops. |
| `memory/services/scheduler.py` | `MaintenanceScheduler.stop` | 104-129 | async method | Cancel both background loops. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._session_activation_loop` | 133-177 | async method | Check every 60s for queued sessions to activate and auto-summarize active ones. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._thinker_discussion_loop` | 181-314 | async method | Spawn dedicated CC subprocesses for active thinker sessions. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._any_thinker_running` | 316-321 | method | True if either server-side Thinker lane is currently running. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._next_thinker_runner` | 323-345 | method | Choose the next server-side Thinker lane from durable DB state. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._record_thinker_turn_failure` | 347-405 | async method | Track first-turn lane failures and fail stuck empty sessions after bounded retries. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._last_thinker_contributor` | 407-420 | async method | Return the last real Thinker lane contributor for a session. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._check_convergence` | 422-517 | async method | Check if the session discussion has converged using the backend model. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._has_explicit_close_agreement` | 520-546 | method | Return True once both Thinker participants emit the close token. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._has_close_motion_ready` | 549-591 | method | Return True when a close token has been ratified by the other lane. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._normalize_thinker_sender` | 594-613 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._has_close_objection` | 616-617 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._has_standalone_close_token` | 620-627 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._check_similarity_runaway` | 629-663 | async method | Force-close if either side has emitted near-identical output in a run. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._token_overlap` | 666-673 | method | Method block. |
| `memory/services/scheduler.py` | `MaintenanceScheduler._finalize_and_notify` | 675-714 | async method | Finalize a session with action extraction and notify the chatroom. |
| `memory/services/scheduler.py` | `MaintenanceScheduler.get_status` | 718-734 | method | Return scheduler status for API endpoint. |
| `memory/services/scheduler.py` | `MaintenanceScheduler.is_running` | 737-738 | method | Method block. |
| `memory/services/thinker.py` | `TokenTracker` | 73-103 | class | Accumulates API usage and estimates cost per model. |
| `memory/services/thinker.py` | `TokenTracker.record` | 81-91 | method | Method block. |
| `memory/services/thinker.py` | `TokenTracker.estimated_cost` | 94-95 | method | Method block. |
| `memory/services/thinker.py` | `TokenTracker.to_dict` | 97-103 | method | Method block. |
| `memory/services/thinker.py` | `PassResult` | 111-133 | class | Result from a single analysis pass. |
| `memory/services/thinker.py` | `PassResult.to_dict` | 123-133 | method | Method block. |
| `memory/services/thinker.py` | `ThinkerService` | 140-770 | class | The Thinker -- Claude Opus analysis engine for the PMS. |
| `memory/services/thinker.py` | `ThinkerService.__init__` | 147-169 | method | Method block. |
| `memory/services/thinker.py` | `ThinkerService._over_budget` | 171-172 | method | Method block. |
| `memory/services/thinker.py` | `ThinkerService._delay` | 174-175 | async method | Async method block. |
| `memory/services/thinker.py` | `ThinkerService._log_reasoning` | 177-188 | async method | No-op: ai_reasoning removed. |
| `memory/services/thinker.py` | `ThinkerService._parse_json` | 190-225 | method | Parse JSON from Claude's response, handling code fences. |
| `memory/services/thinker.py` | `ThinkerService.discover_patterns` | 231-238 | async method | STUB -- patterns table deprecated 2026-04-26. |
| `memory/services/thinker.py` | `ThinkerService.resolve_questions` | 244-254 | async method | Check open questions against the database for answers. |
| `memory/services/thinker.py` | `ThinkerService.synthesize_knowledge` | 260-388 | async method | Synthesize emergent insights from major topic clusters. |
| `memory/services/thinker.py` | `ThinkerService.detect_contradictions` | 394-531 | async method | Detect cross-family contradictions between OpenAI and Anthropic claims. |
| `memory/services/thinker.py` | `ThinkerService.validate_claims` | 537-660 | async method | Validate high-confidence OpenAI claims with corroborating evidence. |
| `memory/services/thinker.py` | `ThinkerService.triage_record` | 671-770 | async method | Event-driven triage: check if a new record connects to anything interesting. |
| `memory/services/thinker_sessions.py` | `write_decision_artifact` | 43-98 | function | Write a finalized session's decision to a durable markdown artifact file. |
| `memory/services/thinker_sessions.py` | `_is_open_loop_seed` | 117-118 | function | Function block. |
| `memory/services/thinker_sessions.py` | `_clean_workshop_topic_label` | 121-129 | function | Return a short UI topic label, or empty string when the finalizer missed. |
| `memory/services/thinker_sessions.py` | `_clip` | 132-133 | function | Function block. |
| `memory/services/thinker_sessions.py` | `_align_item_meta` | 139-164 | function | Pair each raw action item with its finalizer-provided lane/title/why/next-move. |
| `memory/services/thinker_sessions.py` | `ThinkerSession` | 168-244 | class | A single thinker session. |
| `memory/services/thinker_sessions.py` | `ThinkerSession.to_dict` | 189-209 | method | Method block. |
| `memory/services/thinker_sessions.py` | `ThinkerSession.from_row` | 212-244 | method | Method block. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager` | 247-1639 | class | Manages the thinker session queue and lifecycle. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.__init__` | 250-278 | method | Args: conn: Database connection notify_fn: async fn(text, msg_type, metadata) -> posts to chatroom chat_notify_fn: async fn(text) -> posts one-liner to main chat llm: LLMClient for live summary generation topic_boundary_notify_fn: async fn(payload, room_id) -> live-renders a persisted divider task_queue: TaskQueue for creating action item task suggestions. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.init_cooldown` | 280-301 | async method | Load last session activation time from DB so restarts don't flush the cooldown. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.create_session` | 303-386 | async method | Create a new queued thinker session from an auto-approved idea. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.ingest_pending_ideas` | 388-396 | async method | Async method block. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._ingest_pending_ideas` | 398-472 | async method | Pull queued thinker_intake rows into Thinker sessions. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._reject_open_loop_intake` | 474-493 | async method | Tombstone queued open-loop intake before it can seed sessions. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.list_sessions` | 495-522 | async method | List all sessions, optionally filtered by status. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.get_session` | 524-533 | async method | Get a single session by ID. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.activate_next` | 535-569 | async method | Activate the next queued session if cooldown has passed and none active. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.dismiss_open_loop_sessions` | 571-614 | async method | Dismiss active/queued/paused sessions seeded from OPEN LOOP records. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.repair_active_invariant` | 616-705 | async method | Repair stale multi-active state without marking empty sessions complete. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._activate_session` | 707-734 | async method | Activate a session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.add_message` | 736-749 | async method | Record a message posted to a session thread. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.update_summary` | 751-760 | async method | Update the live summary for a session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.pause_session` | 762-782 | async method | Pause an active session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.resume_session` | 784-822 | async method | Resume a paused session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._classify_by_title` | 824-854 | async method | Lightweight category classification from title (+ optional summary). |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.dismiss_session` | 856-879 | async method | Dismiss a session — stops resurfacing it. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.fail_session` | 881-923 | async method | Dismiss a failed session without calling another model. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.complete_session` | 925-962 | async method | Mark a session as done. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.get_session_messages` | 964-1001 | async method | Get all chatroom messages belonging to a session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._write_workshop_topic_boundary` | 1003-1155 | async method | Persist and live-render the Workshop divider for one finalized session. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.finalize_session` | 1157-1431 | async method | Finalize a session — LLM synthesis, archive conclusions to PMS, mark done. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._create_action_item_tasks` | 1433-1506 | async method | Create Actions-tab task suggestions for each action item. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager._fallback_summary_from_messages` | 1509-1548 | method | Build a compact summary when no LLM finalizer is available. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.auto_summarize_active` | 1550-1629 | async method | If the active session has unsummarized messages, re-summarize with the LLM client. |
| `memory/services/thinker_sessions.py` | `ThinkerSessionManager.status` | 1631-1639 | method | Return manager status (sync — for health endpoints). |
| `memory/services/thinker_subprocess.py` | `_StrictFormatDict` | 103-105 | class | Class block. |
| `memory/services/thinker_subprocess.py` | `_StrictFormatDict.__missing__` | 104-105 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `kill_stale_thinker_processes` | 107-129 | function | Kill orphaned thinker model-runner processes from previous runs. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess` | 132-910 | class | Manages thinker subprocess spawning and turn lifecycle. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.__init__` | 135-154 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.is_running` | 157-159 | method | True if a thinker subprocess is currently running. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.current_pid` | 162-163 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.run_turn` | 165-255 | async method | Run one thinker turn for the given session. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.kill_current` | 257-278 | async method | Kill the current thinker subprocess if running. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._spawn_and_capture` | 283-363 | async method | Run one provider-neutral thinker worker turn and return assistant text. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._format_empty_agent_result` | 365-378 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._format_exception` | 381-394 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._diagnostic_tail` | 397-401 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._handle_stdout_line` | 403-438 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._build_system_prompt` | 441-455 | method | Build the system prompt appended to the thinker subprocess. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._role_contract_path` | 457-461 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._load_role_contract` | 463-483 | method | Load this lane's Workshop role contract (Builder/Critic). |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._role_contract_block` | 485-490 | method | Render the role contract as an appendable system-prompt block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._prompt_path` | 492-499 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._prompt_sections` | 501-513 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._prompt_section` | 515-520 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._render_prompt_section` | 522-524 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._render_prompt_parts` | 526-532 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._load_marc_profile` | 534-552 | method | Load the first ~100 lines of marc_profile.md for thinker context. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._load_marc_insights` | 554-570 | method | Load marc_character_insights.md for thinker context. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._format_transcript` | 572-578 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._session_transcript_messages` | 580-594 | method | Return only real conversation turns for prompt transcript building. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._format_pms_section` | 596-609 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._common_prompt_values` | 611-641 | method | Method block. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._build_prompt` | 643-662 | method | Build the user prompt for a thinker turn. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._build_freeform_prompt` | 664-686 | method | Build the prompt for a freeform ideation session. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.run_interactive_turn` | 690-744 | async method | Run an interactive debate response to a human message. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._spawn_and_capture_interactive` | 747-802 | async method | Run one provider-neutral interactive thinker turn. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._build_interactive_system_prompt` | 804-818 | method | Build debate-oriented system prompt for interactive sessions. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._build_interactive_prompt` | 820-835 | method | Build the user prompt for an interactive debate turn. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._fetch_session` | 839-849 | method | Fetch session details from the API. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._fetch_session_messages` | 851-866 | method | Fetch session messages from the API. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._search_pms` | 868-880 | method | Search PMS for records related to the query. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess._post_contribution` | 882-900 | method | POST the analysis to the /contribute endpoint. |
| `memory/services/thinker_subprocess.py` | `ThinkerSubprocess.status` | 902-910 | method | Return current status. |
| `memory/services/workshop_room.py` | `workshop_room_id` | 19-21 | function | Return the room that should display Workshop/Thinker work. |
| `memory/services/workshop_room.py` | `workshop_visible_metadata` | 24-29 | function | Stamp chat metadata so Workshop work is explicit and room-routed. |
| `memory/user_world.py` | `_dotenv_values` | 115-135 | function | Function block. |
| `memory/user_world.py` | `_env_first` | 138-148 | function | Function block. |
| `memory/user_world.py` | `user_world_path` | 151-153 | function | Function block. |
| `memory/user_world.py` | `load_user_world` | 156-172 | function | Load local user-world data. |
| `memory/user_world.py` | `place_world_findings` | 175-229 | function | Return preshaped framing findings for the current resolved place. |
| `memory/user_world.py` | `_place_related_items` | 232-260 | function | Return direct and linked user-world items for one place. |
| `memory/user_world.py` | `_iter_items` | 263-275 | function | Function block. |
| `memory/user_world.py` | `_place_aliases` | 278-287 | function | Function block. |
| `memory/user_world.py` | `_item_belongs_to_place` | 290-304 | function | Function block. |
| `memory/user_world.py` | `_resolve_place` | 307-335 | function | Function block. |
| `memory/user_world.py` | `_bare_place_id` | 338-339 | function | Function block. |
| `memory/user_world.py` | `_raw_message_terms` | 342-347 | function | Function block. |
| `memory/user_world.py` | `_expanded_message_terms` | 350-356 | function | Function block. |
| `memory/user_world.py` | `_matched_trigger` | 359-389 | function | Function block. |
| `memory/user_world.py` | `_item_keywords` | 392-404 | function | Function block. |
| `memory/user_world.py` | `_item_keyword_phrases` | 407-418 | function | Function block. |
| `memory/user_world.py` | `_contains_phrase` | 421-426 | function | Function block. |
| `memory/user_world.py` | `safe_texture_allowed` | 429-434 | function | Return true only for explicitly safe, low-stakes rapport texture. |
| `memory/user_world.py` | `_finding_from_item` | 437-468 | function | Function block. |
| `memory/utils/jsonl_rotation.py` | `rotate_jsonl_if_needed` | 9-25 | function | Rotate an active JSONL file when it has crossed a size cap. |
| `memory/utils/jsonl_rotation.py` | `_prune_archives` | 28-37 | function | Function block. |
| `memory/utils/jsonl_rotation.py` | `_list_archives` | 40-50 | function | Function block. |
| `memory/utils/local_notify.py` | `send_toast` | 25-60 | function | Show a Windows toast notification. |
| `memory/utils/processes.py` | `hidden_subprocess_kwargs` | 12-27 | function | Return subprocess kwargs that suppress console windows on Windows. |
| `memory/utils/processes.py` | `process_cmdline` | 30-38 | function | Best-effort stringified command line for a process. |
| `memory/utils/processes.py` | `process_name` | 41-49 | function | Best-effort lowercase process name. |
| `memory/utils/processes.py` | `find_processes` | 52-78 | function | Find processes matching optional cmdline fragments and process names. |
| `memory/utils/processes.py` | `terminate_process_tree` | 81-128 | function | Terminate a process and its children, escalating to kill if needed. |
| `memory/utils/processes.py` | `tail_file` | 131-152 | function | Read the last N lines of a text file without shelling out to tail. |
| `memory/utils/runtime.py` | `_norm_path_entry` | 40-41 | function | Function block. |
| `memory/utils/runtime.py` | `prepend_path_entries` | 44-73 | function | Prepend PATH entries while preserving order and removing duplicates. |
| `memory/utils/runtime.py` | `_home_path` | 76-80 | function | Function block. |
| `memory/utils/runtime.py` | `_resolve_node_extra_ca_certs` | 83-100 | function | Locate the mkcert root CA so Node-based Claude Code subprocesses trust the local HTTPS listener. |
| `memory/utils/runtime.py` | `build_subprocess_env` | 103-116 | function | Copy the current environment, drop unwanted keys, and prepend PATH entries. |
| `memory/utils/runtime.py` | `subprocess_creationflags` | 119-123 | function | Return Windows subprocess flags used by backend CLI runners. |
| `memory/utils/runtime.py` | `run_subprocess_capture_sync` | 126-153 | function | Run a CLI subprocess without depending on asyncio subprocess support. |
| `memory/utils/runtime.py` | `run_subprocess_capture` | 156-165 | async function | Async wrapper around run_subprocess_capture_sync. |
| `memory/utils/runtime.py` | `resolve_path` | 168-190 | function | Resolve a configured path from env vars or fallback candidates. |
| `memory/utils/runtime.py` | `find_executable` | 193-213 | function | Return the first configured executable path that exists. |
| `memory/utils/runtime.py` | `_claude_search_paths` | 216-217 | function | Function block. |
| `memory/utils/runtime.py` | `_resolve_windows_claude_command` | 220-230 | function | Function block. |
| `memory/utils/runtime.py` | `find_claude_command` | 233-250 | function | Resolve the full command prefix for invoking Claude Code. |
| `memory/utils/runtime.py` | `claude_project_slug` | 253-277 | function | Derive Claude Code's project slug from an absolute project path. |
| `memory/utils/runtime.py` | `claude_project_memory_dir` | 280-293 | function | Return the Claude Code memory directory for a project. |
| `pms_v2/app.py` | `create_app` | 18-137 | function | Function block. |
| `pms_v2/config.py` | `Settings` | 11-17 | class | Class block. |
| `pms_v2/config.py` | `get_settings` | 20-40 | function | Function block. |
| `pms_v2/models.py` | `ActorIdentity` | 16-20 | class | Class block. |
| `pms_v2/models.py` | `Scope` | 23-29 | class | Class block. |
| `pms_v2/models.py` | `ArchiveEnvelope` | 32-49 | class | Class block. |
| `pms_v2/models.py` | `SourceRegistration` | 52-64 | class | Class block. |
| `pms_v2/models.py` | `BatchReplayRequest` | 67-68 | class | Class block. |
| `pms_v2/prompt_wrappers.py` | `_clean` | 58-59 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_is_hot_json_body` | 62-63 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_strip_json_fence` | 66-77 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_json_body` | 80-90 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_is_tool_marker_body` | 93-95 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_is_record_extraction_body` | 98-121 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `_is_control_body` | 124-130 | function | Function block. |
| `pms_v2/prompt_wrappers.py` | `is_non_archival_text_body` | 133-145 | function | Return True for whole-message protocol/control bodies. |
| `pms_v2/prompt_wrappers.py` | `is_prompt_wrapper_content` | 148-150 | function | Return True only when the whole row body is a runtime prompt wrapper. |
| `pms_v2/prompt_wrappers.py` | `is_prompt_wrapper_archive_row` | 153-156 | function | Return True for transcript archive rows that should never be stored. |
| `pms_v2/retrieval.py` | `_now_iso` | 49-50 | function | Function block. |
| `pms_v2/retrieval.py` | `_connect_ro` | 53-62 | function | Function block. |
| `pms_v2/retrieval.py` | `_connect_rw` | 65-72 | function | Function block. |
| `pms_v2/retrieval.py` | `_loads_json` | 75-83 | function | Function block. |
| `pms_v2/retrieval.py` | `_flatten_json` | 86-102 | function | Function block. |
| `pms_v2/retrieval.py` | `_compact` | 105-109 | function | Function block. |
| `pms_v2/retrieval.py` | `_tokens_for_query` | 112-120 | function | Function block. |
| `pms_v2/retrieval.py` | `_table_exists` | 123-128 | function | Function block. |
| `pms_v2/retrieval.py` | `_archive_source_count` | 131-136 | function | Function block. |
| `pms_v2/retrieval.py` | `default_index_path` | 139-142 | function | Function block. |
| `pms_v2/retrieval.py` | `rebuild_retrieval_index` | 145-310 | function | Function block. |
| `pms_v2/retrieval.py` | `retrieval_index_status` | 313-314 | function | Function block. |
| `pms_v2/retrieval.py` | `index_archive_rows` | 317-395 | function | Function block. |
| `pms_v2/retrieval.py` | `_archive_index_payload` | 398-439 | function | Function block. |
| `pms_v2/retrieval.py` | `_fts_archive_search` | 481-532 | function | Run a single FTS5 MATCH search over an archive content table. |
| `pms_v2/retrieval.py` | `search_archive` | 535-607 | function | Function block. |
| `pms_v2/runtime_log.py` | `_target_db_path` | 14-17 | function | Function block. |
| `pms_v2/runtime_log.py` | `log_runtime_conversation` | 20-79 | function | Append runtime/subprocess output to the v2 conversation archive. |
| `pms_v2/shadow_client.py` | `_chatroom_message_source` | 20-24 | function | Function block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient` | 27-289 | class | Buffers PMS v2 shadow events to disk, then ships them in the background. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.__init__` | 30-44 | method | Method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.start` | 46-51 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.stop` | 53-62 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.emit_archive` | 64-65 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.emit_chatroom_message` | 67-112 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.emit_conversation_message` | 114-152 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.emit_reaction_snapshot` | 154-198 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.outbox_depth` | 200-203 | method | Method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient.flush_once` | 205-215 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._enqueue` | 217-230 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._shipper_loop` | 232-247 | async method | Async method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._deliver_file` | 249-261 | method | Method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._post_json` | 263-272 | method | Method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._normalize_reactions` | 275-281 | method | Method block. |
| `pms_v2/shadow_client.py` | `ShadowEventClient._is_acked_file` | 284-289 | method | Method block. |
| `pms_v2/store.py` | `_row_dict` | 231-232 | function | Function block. |
| `pms_v2/store.py` | `_loads_json` | 235-240 | function | Function block. |
| `pms_v2/store.py` | `_effective_sensitivity` | 243-247 | function | Function block. |
| `pms_v2/store.py` | `_default_actor_type` | 250-257 | function | Function block. |
| `pms_v2/store.py` | `_default_display_name` | 260-262 | function | Function block. |
| `pms_v2/store.py` | `_json_list` | 265-274 | function | Function block. |
| `pms_v2/store.py` | `_json_array_text` | 277-278 | function | Function block. |
| `pms_v2/store.py` | `_clean_identity` | 281-287 | function | Function block. |
| `pms_v2/store.py` | `_participant_identity` | 290-316 | function | Function block. |
| `pms_v2/store.py` | `_parse_timestamp` | 319-329 | function | Function block. |
| `pms_v2/store.py` | `_days_ago_iso` | 332-334 | function | Function block. |
| `pms_v2/store.py` | `ShadowStore` | 337-1599 | class | Class block. |
| `pms_v2/store.py` | `ShadowStore.__init__` | 339-346 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.initialize` | 348-365 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.close` | 367-372 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._connect` | 374-383 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._is_database_locked` | 386-387 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._run_deferred_write_transaction` | 389-409 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._migrate_schema` | 411-619 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._seed_defaults` | 621-640 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._upsert_source_registration` | 642-693 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.register_source` | 695-708 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._ensure_actor` | 711-741 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._resolve_scope` | 743-781 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._source_registration_row` | 784-785 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._require_source_registration` | 787-793 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._buffer_envelope` | 795-804 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._record_ingest_failure` | 806-817 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._latest_archive_success` | 819-857 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._latest_success` | 859-881 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.ingest_archive` | 883-895 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.ingest_archive_batch` | 897-927 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._insert_specialized_row` | 930-1013 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._insert_room_event` | 1015-1021 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._archive_conversation_key` | 1023-1029 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._archive_topic_label` | 1031-1041 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._assign_archive_session` | 1043-1101 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._insert_import_log` | 1103-1134 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._insert_ingestion_event` | 1136-1143 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._link_scope` | 1145-1148 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._room_summary` | 1150-1158 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._ingest_archive_with_conn` | 1160-1247 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._queue_live_processing_job` | 1249-1302 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.list_live_processing_jobs` | 1304-1333 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.process_live_processing_jobs` | 1335-1438 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore._archive_row_has_text` | 1440-1447 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.replay_batch` | 1450-1473 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.retry_failed_batch` | 1475-1487 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.health_snapshot` | 1490-1505 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.list_room_events` | 1507-1521 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.list_import_batches` | 1523-1531 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.list_ingest_metrics` | 1533-1568 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.get_source_registration` | 1570-1583 | method | Method block. |
| `pms_v2/store.py` | `ShadowStore.list_source_registrations` | 1585-1599 | method | Method block. |
| `pms_v2/utils.py` | `now_iso` | 10-11 | function | Function block. |
| `pms_v2/utils.py` | `make_id` | 14-15 | function | Function block. |
| `pms_v2/utils.py` | `stable_json` | 18-19 | function | Function block. |
| `pms_v2/utils.py` | `hash_payload` | 22-24 | function | Function block. |
| `shell/app.py` | `_log` | 23-31 | function | Append to the shell log — the window must never fail silently. |
| `shell/app.py` | `chatroom_url` | 34-36 | function | Localhost HTTP chatroom URL — no TLS, no cert warnings, same machine. |
| `shell/app.py` | `_write_integrity_status` | 39-60 | function | Persist the integrity verdict so support (and a future in-app banner) can read it. |
| `shell/app.py` | `_show_modified_core_banner` | 63-78 | function | Inject a visible 'modified core' banner into the boot page. |
| `shell/app.py` | `_check_core_integrity` | 81-102 | function | Verify the sealed core at boot. |
| `shell/app.py` | `_resolve_gpu_mode` | 105-131 | function | GPU rendering mode for the WebView2 host: 'auto' \| 'on' \| 'off'. |
| `shell/app.py` | `_apply_gpu_mode` | 134-155 | function | Translate the GPU mode into WebView2 (Chromium) command-line flags. |
| `shell/app.py` | `_wait_for_api` | 158-167 | function | Function block. |
| `shell/app.py` | `_centered_xy` | 235-267 | function | Top-left (x, y) that centers a width x height window on the primary monitor's work area (taskbar excluded), clamped so the window can never spill past the screen edges. |
| `shell/app.py` | `_enable_native_context_menu` | 270-303 | function | Re-enable WebView2's native right-click menu (copy/paste/select-all) WITHOUT turning on full debug mode. |
| `shell/app.py` | `_open_localhost_windows_in_shell` | 306-370 | function | Make window.open / target=_blank for SC's OWN urls open a new shell window instead of ejecting to the OS default browser (Edge). |
| `shell/app.py` | `_our_shell_windows` | 373-417 | function | Top-level windows that are genuinely OUR shell: [(hwnd, is_visible)]. |
| `shell/app.py` | `_focus_existing_window` | 420-447 | function | If a VISIBLE SC shell window exists, bring it forward instead of doubling. |
| `shell/app.py` | `main` | 450-564 | function | Function block. |

## Notes

* This index covers only the files directly inside this folder. Open a child folder's `_INDEX.md` for deeper detail.
* Cache and generated folders like `__pycache__/` are intentionally omitted.
