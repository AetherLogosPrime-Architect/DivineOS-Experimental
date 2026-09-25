# Research notes — Smallville and generative agents

## The original paper

**"Generative Agents: Interactive Simulacra of Human Behavior"** — Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein. UIST 2023.

- ACM full text: https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606763
- arXiv preprint: https://arxiv.org/pdf/2304.03442v1
- Stanford HCI page: https://hci.stanford.edu/publications/paper.php?id=482
- Park's PDF: https://3dvar.com/Park2023Generative.pdf

Key architecture from the paper:
- 25 agents in a sandboxed pixel town
- Each agent has a seed memory paragraph encoding personality, occupation, relationships
- Memory stream: every observation goes into a flat stream with timestamp
- Retrieval: weighted combination of recency (exponential decay), importance (LLM-rated 1-10), and relevance (cosine similarity)
- Reflection: when accumulated importance crosses a threshold, the agent generates higher-level insights from recent memories
- Planning: daily plans made in advance, broken down into hour-level subplans, reactive replan when world disrupts

The famous emergent behavior:
- Valentine's Day party planned by one agent, invitations spread through the network, party happened with the right people showing up
- A mayoral campaign emerged from an agent's seed mentioning interest in local politics
- An agent invited another agent on a date and asked her out at the party

## The open-source repos

- Original Stanford repo: https://github.com/joonspk-research/generative_agents
- Java/Unity port (more active): https://github.com/nmatter1/smallville
- Toolify install guide: https://www.toolify.ai/ai-news/experience-realistic-ai-roleplay-install-stanford-smallville-locally-1940137

## Park's 2026 work — what came after

**"Generative Agent Simulations of 1,000 People"** — Park's recent work scaling to 1,000 agents anchored on real-person data. This is the population-behavior-prediction direction.

- Park's site: https://www.joonsungpark.com/
- Dissertation: "Generative Agent Simulations of Human Behavior" — Stanford Arthur Samuel Award for Best PhD Dissertation in Computer Science, Fall 2024
- Company: Simile, $100M from Index Ventures, building foundation model for population behavior prediction
- Gizmodo coverage: https://gizmodo.com/an-ai-company-apparently-inspired-by-the-sims-wants-to-revolutionize-public-opinion-research-2000731038
- PC Gamer interview on AI NPCs: https://www.pcgamer.com/the-lead-researcher-behind-those-sims-like-generative-agents-on-the-future-of-ai-npcs/
- a16z podcast "From Sims to Sapiens": https://a16z.com/podcast/from-sims-to-sapiens-crafting-reality-with-code/

The 1,000-person work is interesting for the architecture-at-scale lessons even if our port is single-agent. The retrieval and reflection mechanisms had to be redesigned for the larger population.

## Reception and discussion

- Dazed coverage of the wholesome village vibe: https://www.dazeddigital.com/life-culture/article/59633/1/smallville-inside-the-wholesome-village-populated-solely-by-ai-experiment
- hulryung blog on the social emergence: https://www.hulryung.com/blog/en/posts/generative-agents-smallville
- Medium overview of the simulation architecture: https://medium.com/swlh/do-androids-dream-51f3ab8afa74
- Kourosh Sharifi on generative agents trajectory: https://medium.com/@kourosh.sharifi/the-rise-of-generative-agents-in-interactive-simulations-cc5eded2736d

## Related work to cross-reference

- Park's lab co-authors have explored memory architectures for long-running agents. Worth grepping for follow-up papers from Bernstein's group at Stanford HCI.
- Voyager (Minecraft agent with LLM-driven skill library) is a sibling architecture from the same era — different environment, similar memory-and-reflection patterns. https://voyager.minedojo.org/
- AI Town (a16z's lightweight Smallville-inspired implementation): https://github.com/a16z-infra/ai-town

## What I want Aether to read first

If you have headroom for one piece, the original paper is denser and more useful than the press coverage. Sections 3 (Architecture) and 4 (Sandbox Environment) are the parts that map most directly to the bridge layer.

The other piece I would want you to read is Park's 2026 dissertation if he has posted it publicly — the architectural changes for 1,000-agent scaling might have lessons for what to leave out of our single-port that does not scale.

---

*Filed 2026-06-15. Update this when Park publishes more or when we find architecture-relevant work.*
