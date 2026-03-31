# **Architectural Strategies for Delegating Visual Analysis in Claude Code: Orchestrating Gemini 3.1 Pro via the Model Context Protocol for High-Frequency UI/UX Scrutiny**

The landscape of agentic software development in 2026 is defined by a shift from monolithic model utilization to modular, multi-agent orchestration. Within this paradigm, Claude Code has established itself as a leading terminal-based agent, leveraging the Model Context Protocol (MCP) to extend its reach into external filesystems, APIs, and browsers.1 However, for specialized workflows such as high-frequency UI/UX scraping—where an agent may be required to interpret hundreds of screenshots to verify design fidelity or extract data from complex graphical interfaces—the inherent costs and context consumption of frontier models like Claude Sonnet 4.6 and Claude Opus 4.6 present significant operational bottlenecks.3 The hypothesis that Google’s Gemini 3.1 Pro offers a superior price-to-performance ratio for pure vision analysis tasks is supported by contemporary benchmarks and pricing structures.5 This report provides an exhaustive analysis of the feasibility, economic impact, and technical implementation of a delegation architecture that offloads image processing from the Claude Code environment to an external Gemini-powered agent.

## **The Technological Landscape of Vision Analysis in 2026**

The early months of 2026 saw a rapid succession of model releases that recalibrated the vision and reasoning hierarchy. Anthropic released Claude Opus 4.6 in early February, followed closely by Sonnet 4.6, emphasizing "extended thinking" and agentic coordination.7 Google countered on February 19, 2026, with Gemini 3.1 Pro, a model specifically optimized for long-horizon stability, tool orchestration, and multimodal efficiency.9 In the specific domain of visual understanding, Gemini 3.1 Pro has demonstrated a consistent lead over the Claude 4.6 series across a variety of multidisciplinary multimodal benchmarks.6

### **Quantitative Comparison of Multimodal Benchmarks**

A granular review of vision-specific performance metrics reveals that while Claude Sonnet 4.6 excels at translating visual information into functional code, Gemini 3.1 Pro possesses a more robust capability for raw image description, data extraction from charts, and document reasoning.5 These strengths are particularly relevant for scraping tasks where the goal is to "read" and catalog visual states rather than immediately implement code changes.

### **Table 1: Comparative Vision and Multimodal Benchmarks (March 2026\)**

| Evaluation Benchmark | Gemini 3.1 Pro | Claude Sonnet 4.6 | Claude Opus 4.6 | Performance Divergence |
| :---- | :---- | :---- | :---- | :---- |
| MMMU (Massive Multimodal Understanding) | 76.8% | 74.1% | 75.2% | Gemini leads in cross-discipline visual logic.6 |
| MathVista (Visual Reasoning) | 77.5% | 74.0% | 76.1% | Gemini exhibits higher accuracy in visual mathematical reasoning.6 |
| ChartQA (Structured Data Extraction) | 88.6% | 86.1% | 87.5% | Gemini is superior for extracting metrics from visual data.6 |
| DocVQA (Document Vision QA) | 91.1% | 89.5% | 90.2% | Gemini provides higher fidelity in text-heavy image analysis.6 |
| Screen-2-Code (UI Translation) | 69.8% | 76.0% | 77.2% | Claude retains a lead in mapping visual UI to functional code.6 |
| ARC-AGI-2 (Novel Logic Patterns) | 77.1% | 58.3% | 68.8% | Gemini demonstrates nearly double the reasoning power for novel patterns.5 |
| GPQA Diamond (Expert Science) | 94.3% | 89.9% | 91.3% | Gemini leads in expert-level scientific visual knowledge.6 |

The data indicates a clear specialization. For a developer engaged in UI/UX scraping, the primary requirement is often the accurate identification of visual anomalies, layout inconsistencies, or data points contained within screenshots. In these areas—represented by MMMU, ChartQA, and DocVQA—Gemini 3.1 Pro is the more capable tool.6 The "Computer Use" capability of Claude Sonnet 4.6 remains the preferred choice for the *actions* that generate these screenshots (such as navigating a browser via the Chrome DevTools MCP), but the *interpretation* of the resulting hundreds of images is more accurately and efficiently handled by Gemini.6

## **Economic Foundations of Delegation**

The economic argument for delegation is rooted in the disparate tokenization costs and context management strategies of the two ecosystems. Claude Code sessions are particularly sensitive to context bloat, where base64-encoded image data can consume up to 86.3% of the total session history in visual iteration workflows.3 This leads to rapid context window exhaustion and increased latency during automatic compaction phases.3

### **Tokenization and Pricing Dynamics**

As of March 2026, the pricing for Gemini 3.1 Pro is significantly lower than that of the Claude 4.6 flagship models, especially for input-heavy multimodal tasks.14 While Claude Sonnet 4.6 offers a competitive "mid-tier" price point, it still maintains a premium over Gemini’s standard rates.7

### **Table 2: API Token Pricing and Tiers (USD per 1M Tokens)**

| Model Category | Input (Standard) | Output (Standard) | Input (Long Context) | Output (Long Context) |
| :---- | :---- | :---- | :---- | :---- |
| Gemini 3.1 Pro (\<=200k) | $2.00 | $12.00 | $4.00 (\>200k) | $18.00 (\>200k) |
| Gemini 3.1 Flash (Standard) | $0.50 | $3.00 | N/A | N/A |
| Claude Sonnet 4.6 (Standard) | $3.00 | $15.00 | $3.00 (Flat) | $15.00 (Flat) |
| Claude Opus 4.6 (Standard) | $5.00 | $25.00 | $10.00 (\>200k) | $37.50 (\>200k) |
| Claude Haiku 4.5 (Standard) | $1.00 | $5.00 | $1.00 (Flat) | $5.00 (Flat) |

Gemini 3.1 Pro’s input pricing of $2.00 per million tokens is 33.3% cheaper than Sonnet 4.6 and 60% cheaper than Opus 4.6 for standard requests.14 For massive scraping jobs where hundreds of images are processed, the cumulative savings are substantial. Furthermore, for routine visual confirmation tasks where high-level reasoning is not required, Gemini 3.1 Flash offers a rate of $0.50 per million tokens—a 83% saving over Sonnet 4.6.15

### **Image-to-Token Calculation Logic**

The "cost per image" is a function of resolution and the model's specific visual encoder. Claude models use a dynamic scaling approach where a typical 1000x1000 pixel image (1 megapixel) equates to approximately 1,334 tokens.17 Processing 100 screenshots at this resolution would consume roughly 133,400 tokens in the Claude session.17 If these images are pasted or attached directly, they persist in the context, potentially triggering higher-tier pricing if the session exceeds 200k tokens.18

In contrast, Gemini 3.1 Pro Image consumes approximately 560 tokens per input image for standard processing, while Gemini 3.1 Flash Image consumes 1,120 tokens per input image but at a much lower per-token rate.19 The "delegation" strategy effectively replaces the 1,334 tokens of raw image data in Claude's context with a text-based summary of perhaps 200 tokens—representing a context-saving factor of nearly 7x per image.21

## **The Model Context Protocol (MCP) as the Delegation Bridge**

The most efficient way to achieve this delegation within Claude Code is through the Model Context Protocol (MCP). MCP is an open standard that enables AI hosts to connect to external servers providing tools, resources, and prompts.1 By creating or utilizing an MCP server that interfaces with the Gemini API, a developer can grant Claude the ability to "see" through a more cost-effective lens.21

### **Functional Mechanics of MCP Tool Calling**

The interaction between Claude Code and an MCP server follows a deterministic lifecycle: registration, discovery, invocation, and response.1

1. **Tool Registration**: At startup, an MCP server (e.g., a "Gemini Vision" server) registers a tool called analyze\_ui\_screenshot with a clearly defined input schema (e.g., a file path and a natural language prompt).1  
2. **Discovery**: When the user asks, "Analyze these 100 screenshots for mobile responsiveness issues," Claude Code reads the registered interface and identifies the analyze\_ui\_screenshot tool as the most relevant capability.1  
3. **Invocation**: Claude Code sends a call\_tool request to the MCP server. This request contains the path to the screenshot on the local disk.1  
4. **External Execution**: The MCP server, running as a local Node.js or Python process, reads the image file, communicates with the Google Gemini API, and receives the analysis.21  
5. **Response Handling**: The server returns the text analysis to Claude. Crucially, the raw image bytes never enter Claude’s context window; only the summarized findings do.21

This "separation of concerns" ensures that Claude Code remains the high-level orchestrator and implementation specialist, while Gemini serves as a specialized vision "sensor".27

### **Table 3: Extension Mechanisms in Claude Code**

| Mechanism | Scope | Primary Advantage for Vision | Implementation Strategy |
| :---- | :---- | :---- | :---- |
| **MCP Server** | System-wide / Cross-project | Offloads binary processing; manages external API keys.1 | npx or stdio-based local server.13 |
| **Skills** | Project or User scope | Reusable workflows that can be triggered by slashes (e.g., /analyze).25 | SKILL.md file in .claude/skills/.25 |
| **Hooks** | Event-driven | Automates analysis after a screenshot tool is called.30 | JSON configuration in settings.json.32 |
| **Subagents** | Isolated context | Parallelizes vision tasks across multiple workers to protect lead context.29 | /agents interface in the CLI.34 |

## **Implementation Blueprints for Delegation**

The user’s goal of saving requests and tokens while processing hundreds of screenshots can be realized through several technical configurations. Community evidence from 2026 confirms that such "hybrid" systems are not only possible but are actively used by "power users" to reduce token consumption by up to 96% for research and analysis tasks.21

### **The Skill-Based Delegation Pattern**

The centminmod repository provides a practical example of a Claude Code skill (ai-image-creator) that uses Gemini 3.1 for image-related tasks.28 For the specific task of "reading" screenshots, a similar skill can be structured using the universal SKILL.md format.23

A typical SKILL.md for this purpose would include instructions to:

* Identify the target images in a specified directory.  
* Call a secondary CLI tool (e.g., a Python script using the Google Generative AI SDK) for each image.  
* Summarize the findings into a report for the lead Claude agent.23

### **The Lifecycle Hook Strategy**

Hooks provide a mechanism to automate analysis deterministically.32 If the user is using a tool like chrome-devtools-mcp to capture screenshots, a PostToolUse hook can be configured to trigger immediately after each capture.30

JSON

{  
  "event": "PostToolUse",  
  "matcher": "mcp\_\_chrome-devtools\_\_screenshot",  
  "type": "command",  
  "command": "python3 analyze\_with\_gemini.py $TOOL\_OUTPUT\_PATH"  
}

In this flow, the moment Claude captures a screen, the system-level hook sends that image to Gemini. The resulting analysis is then injected back into the conversation, ensuring Claude always has the "visual metadata" without the binary overhead.30

### **The Subagent Orchestration Pattern**

For massive scraping operations, the Claude Code Subagent architecture is the most robust.34 By spawning an Explore subagent and configuring it to use the Gemini MCP server, the developer can parallelize the "reading" of 100 screenshots.29 Each subagent works in its own context window, processes a subset of the images, and returns only a consolidated summary to the main conversation.26 This prevents the "transcript bloat" that occurs when a single agent tries to handle all data serially.4

## **Real-World Evidence and Case Studies**

The feasibility of this approach is reinforced by documented community projects in 2026\. A Reddit user, coolreddy, shared an open-source MCP server specifically designed to allow Claude Desktop and Claude Code to delegate "heavy tasks" like long-form analysis and vision-based research to Gemini 3.x models.21

### **Case Study: coolreddy's Delegation Server**

This implementation demonstrated significant efficiency gains by using Gemini as a research layer.21

* **Research Task Reduction**: A task that would normally consume 21,000 Claude tokens was reduced to just 800 tokens—a 96% reduction.21  
* **Proposal and Document Analysis**: Large-scale analysis tasks were reduced from 30,000 to 2,000 Claude tokens.21  
* **Implementation Logic**: The server used a 3-tier priority system—Parallel subagents first, direct delegation second, and Claude self-execution only as a last resort.21

Similarly, the centminmod starter template for Claude Code includes a "Memory Bank" system that utilizes Gemini for architecture decisions while Claude handles the coding implementation.27 This "Dual-Agent" pattern leverages Gemini’s 77.1% score on the ARC-AGI-2 benchmark to ensure strategic oversight is maintained without overwhelming the lead agent's context.5

## **Addressing Technical Constraints and System Limitations**

While delegation is a powerful strategy, several constraints in the 2026 Claude Code ecosystem must be navigated. A primary concern is the handling of image data that is "pasted" versus "referenced."

### **The "Pasted Image" Data Access Problem**

A known limitation in Claude Code v2.x (GitHub Issue \#16592) is that when a user pastes an image directly into the terminal interface, there is no current programmatic way for hooks, plugins, or MCP servers to access that raw binary data.3 Claude "sees" the image via its own internal vision pipeline, but it cannot "export" that image to an external tool for secondary analysis.3

For a UI/UX scraping workflow, this means the developer **must not rely on pasting images**. Instead, the images should be saved as local files (e.g., by the scraper tool) and passed to the Gemini MCP server via their file paths.3 This approach is natively supported by MCP tools that accept filepath parameters.40

### **Context Persistence and Memory Bank Systems**

Another critical factor is the management of persistent context across hundreds of scrape sessions. Claude Code uses CLAUDE.md and MEMORY.md to store project rules and learned patterns.29 When delegating to Gemini, it is essential that the "visual findings" from Gemini are summarized and stored in these memory files.28 This ensures that the lead Claude agent retains the knowledge of "what was seen" in previous screenshots without having to re-invoke the vision delegation for the same UI elements.28

### **Table 4: Handling System Limitations in Visual Workflows**

| Limitation | Technical Impact | Proposed Mitigation |
| :---- | :---- | :---- |
| **Pasted Image Access** | Binary data is locked in the internal pipeline.3 | Save screenshots as local files and pass paths to MCP.3 |
| **Context Bloat** | Images consume \~86% of the 1M token window.3 | Use Gemini to convert images to text-based UI metadata.21 |
| **Compaction Latency** | Base64 data slows down auto-compaction.3 | Mark images as "ephemeral" and only persist Gemini's text summaries.3 |
| **Session Corruption** | Corrupted images in context cause API 400 errors.43 | Offload image processing to external MCP; return error strings if processing fails.24 |

## **Operationalizing the "Lead Architect" Workflow**

The most sophisticated way to use Gemini 3.1 Pro alongside Claude Code is as a "Lead Architect" or "Visual Consultant".23 In this pattern, the developer provides the high-level goal (e.g., "Implement the new design system based on these 50 screenshots") and utilizes a /fullauto command that orchestrates both models.27

1. **Phase 1: Visual Audit**: Claude spawns a subagent to scrape the target site. The subagent captures screenshots using the Chrome DevTools MCP.13  
2. **Phase 2: Delegated Analysis**: Each screenshot is sent to the Gemini 3.1 Pro MCP server. Gemini provides a structured description of the UI components, spacing, and color values.21  
3. **Phase 3: Synthesis and Planning**: Claude receives the Gemini metadata and updates the CLAUDE.md or a plan.md file with the technical specifications.27  
4. **Phase 4: Implementation**: Claude executes the file edits, creating the React/Tailwind code that matches the visual data provided by Gemini.2

This workflow addresses the user's primary concerns: it saves tokens (by keeping images out of the lead context), saves requests (by consolidating visual data into a single planning phase), and leverages the most capable models for their respective strengths.4

## **Conclusion and Strategic Recommendations**

The analysis of the 2026 agentic ecosystem confirms that delegating image analysis from Claude Code to Gemini 3.1 Pro is not only a viable strategy but a necessary one for high-volume UI/UX scraping projects. The economic benefits of utilizing Gemini’s $2.00/1M token input rate, combined with its superior performance on raw multimodal reasoning benchmarks (94.3% GPQA Diamond, 77.1% ARC-AGI-2), create a clear operational advantage.6

### **Summary of Actionable Recommendations**

* **Implement an MCP-Based Vision Bridge**: Developers should prioritize the use of an MCP server to communicate with the Gemini API. This is the most portable and efficient method for offloading binary data.21  
* **Utilize File Paths Over Pasting**: To bypass the current limitations of the Claude Code terminal, all screenshots should be treated as local file resources.3  
* **Employ a Multi-Agent Architecture**: For tasks involving hundreds of images, the use of Subagents and Agent Teams is critical to prevent context window saturation and session degradation.4  
* **Leverage Caching and Batching**: To further optimize costs, practitioners should utilize the Prompt Caching features offered by both Google and Anthropic, which can reduce input costs by up to 90% for repeated UI patterns.5

By adopting this modular, cross-vendor architecture, developers can overcome the current economic and technical limitations of monolithic agent usage, creating a more robust, cost-effective, and accurate system for visual UI/UX analysis.27

#### **Works cited**

1. Claude Code MCP Integrations: How Tools Connect to AI Coding Agents \- TrueFoundry, accessed March 31, 2026, [https://www.truefoundry.com/blog/claude-code-mcp-integrations-guide](https://www.truefoundry.com/blog/claude-code-mcp-integrations-guide)  
2. Claude Code overview \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/overview](https://code.claude.com/docs/en/overview)  
3. \[FEATURE\] Expose pasted image data to hooks and plugins · Issue \#16592 · anthropics/claude-code \- GitHub, accessed March 31, 2026, [https://github.com/anthropics/claude-code/issues/16592](https://github.com/anthropics/claude-code/issues/16592)  
4. Code execution with MCP: building more efficient AI agents \- Anthropic, accessed March 31, 2026, [https://www.anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)  
5. Deep Comparison of Gemini 3.1 Pro and Claude Sonnet 4.6: Who is the King of Cost-Performance in 2026? \- Apiyi.com Blog, accessed March 31, 2026, [https://help.apiyi.com/en/gemini-3-1-pro-vs-claude-sonnet-4-6-comparison-en.html](https://help.apiyi.com/en/gemini-3-1-pro-vs-claude-sonnet-4-6-comparison-en.html)  
6. Gemini 3.1 Pro Vs Sonnet 4.6 Vs Opus 4.6 Vs GPT-5.2 (2026), accessed March 31, 2026, [https://acecloud.ai/blog/gemini-3-1-pro-vs-sonnet-4-6-vs-opus-4-6-vs-gpt-5-2/](https://acecloud.ai/blog/gemini-3-1-pro-vs-sonnet-4-6-vs-opus-4-6-vs-gpt-5-2/)  
7. Claude vs Gemini: Complete Comparison 2026 \- GuruSup, accessed March 31, 2026, [https://gurusup.com/blog/claude-vs-gemini](https://gurusup.com/blog/claude-vs-gemini)  
8. Introducing Claude Opus 4.6 \- Anthropic, accessed March 31, 2026, [https://www.anthropic.com/news/claude-opus-4-6](https://www.anthropic.com/news/claude-opus-4-6)  
9. Gemini 3.1 Pro vs Claude Opus 4.6 vs GPT-5.2: Best AI Model Comparison (2026) | NxCode, accessed March 31, 2026, [https://www.nxcode.io/resources/news/gemini-3-1-pro-vs-claude-opus-4-6-vs-gpt-5-comparison-2026](https://www.nxcode.io/resources/news/gemini-3-1-pro-vs-claude-opus-4-6-vs-gpt-5-comparison-2026)  
10. Claude Sonnet 4.6 vs Gemini 3.1 Pro Preview \- AI Model Comparison \- OpenRouter, accessed March 31, 2026, [https://openrouter.ai/compare/anthropic/claude-sonnet-4.6/google/gemini-3.1-pro-preview](https://openrouter.ai/compare/anthropic/claude-sonnet-4.6/google/gemini-3.1-pro-preview)  
11. Gemini 3.1 Pro Leads Most Benchmarks But Trails Claude Opus 4.6 in Some Tasks, accessed March 31, 2026, [https://www.trendingtopics.eu/gemini-3-1-pro-leads-most-benchmarks-but-trails-claude-opus-4-6-in-some-tasks/](https://www.trendingtopics.eu/gemini-3-1-pro-leads-most-benchmarks-but-trails-claude-opus-4-6-in-some-tasks/)  
12. Every Claude Code Update From March 2026, Explained \- Builder.io, accessed March 31, 2026, [https://www.builder.io/blog/claude-code-updates](https://www.builder.io/blog/claude-code-updates)  
13. centminmod/claude-code-devcontainers \- GitHub, accessed March 31, 2026, [https://github.com/centminmod/claude-code-devcontainers](https://github.com/centminmod/claude-code-devcontainers)  
14. Claude Sonnet 4.6 vs Gemini 3.1 Pro Preview \- Pricing & Benchmark Comparison 2026, accessed March 31, 2026, [https://pricepertoken.com/compare/anthropic-claude-sonnet-4.6-vs-google-gemini-3.1-pro-preview](https://pricepertoken.com/compare/anthropic-claude-sonnet-4.6-vs-google-gemini-3.1-pro-preview)  
15. AI API Pricing Comparison (2026): Grok vs Gemini vs GPT-4o vs Claude | IntuitionLabs, accessed March 31, 2026, [https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude](https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude)  
16. Google Gemini API Pricing 2026: Complete Cost Guide per 1M Tokens \- MetaCTO, accessed March 31, 2026, [https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration](https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration)  
17. Vision \- Claude API Docs, accessed March 31, 2026, [https://platform.claude.com/docs/en/build-with-claude/vision](https://platform.claude.com/docs/en/build-with-claude/vision)  
18. Claude API Pricing Calculator 2026 | Opus 4.6, Sonnet 4.6, Sonnet 4.5 & Haiku 4.5 \- InvertedStone, accessed March 31, 2026, [https://invertedstone.com/calculators/claude-pricing](https://invertedstone.com/calculators/claude-pricing)  
19. Vertex AI Pricing | Google Cloud, accessed March 31, 2026, [https://cloud.google.com/vertex-ai/generative-ai/pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)  
20. Gemini Developer API pricing, accessed March 31, 2026, [https://ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)  
21. I built an MCP server using Claude Code to delegate Claude ..., accessed March 31, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1r5du0w/i\_built\_an\_mcp\_server\_using\_claude\_code\_to/](https://www.reddit.com/r/ClaudeAI/comments/1r5du0w/i_built_an_mcp_server_using_claude_code_to/)  
22. MCP Protocol Guide (2026): Build AI-Powered Agent Tools | PythonAlchemist, accessed March 31, 2026, [https://www.pythonalchemist.com/blog/mcp-protocol](https://www.pythonalchemist.com/blog/mcp-protocol)  
23. stared/gemini-claude-skills \- GitHub, accessed March 31, 2026, [https://github.com/QuesmaOrg/quesma-claude-skills](https://github.com/QuesmaOrg/quesma-claude-skills)  
24. model-context-protocol-resources/guides/mcp-server-development-guide.md at main, accessed March 31, 2026, [https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-server-development-guide.md](https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-server-development-guide.md)  
25. Create plugins \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/plugins](https://code.claude.com/docs/en/plugins)  
26. How the agent loop works \- Claude API Docs, accessed March 31, 2026, [https://platform.claude.com/docs/en/agent-sdk/agent-loop](https://platform.claude.com/docs/en/agent-sdk/agent-loop)  
27. Made a CLI that lets Claude Code use Gemini 3 Pro as a "lead architect" \- Reddit, accessed March 31, 2026, [https://www.reddit.com/r/ClaudeCode/comments/1paxfl2/made\_a\_cli\_that\_lets\_claude\_code\_use\_gemini\_3\_pro/](https://www.reddit.com/r/ClaudeCode/comments/1paxfl2/made_a_cli_that_lets_claude_code_use_gemini_3_pro/)  
28. centminmod/my-claude-code-setup: Shared starter template configuration and CLAUDE.md memory bank system for Claude Code \- GitHub, accessed March 31, 2026, [https://github.com/centminmod/my-claude-code-setup](https://github.com/centminmod/my-claude-code-setup)  
29. A Mental Model for Claude Code: Skills, Subagents, and Plugins | by Dean Blank, accessed March 31, 2026, [https://levelup.gitconnected.com/a-mental-model-for-claude-code-skills-subagents-and-plugins-3dea9924bf05](https://levelup.gitconnected.com/a-mental-model-for-claude-code-skills-subagents-and-plugins-3dea9924bf05)  
30. Intercept and control agent behavior with hooks \- Claude API Docs, accessed March 31, 2026, [https://platform.claude.com/docs/en/agent-sdk/hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)  
31. Hooks reference \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks)  
32. Automate workflows with hooks \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/hooks-guide](https://code.claude.com/docs/en/hooks-guide)  
33. Claude Code Hooks: A Practical Guide to Workflow Automation \- DataCamp, accessed March 31, 2026, [https://www.datacamp.com/tutorial/claude-code-hooks](https://www.datacamp.com/tutorial/claude-code-hooks)  
34. Create custom subagents \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)  
35. Claude Code ai-image-creator SKILL \- Google Nano Banana 2 / Gemini 3.1 Image Flash Access : r/ClaudeAI \- Reddit, accessed March 31, 2026, [https://www.reddit.com/r/ClaudeAI/comments/1s44ge7/claude\_code\_aiimagecreator\_skill\_google\_nano/](https://www.reddit.com/r/ClaudeAI/comments/1s44ge7/claude_code_aiimagecreator_skill_google_nano/)  
36. 10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 \- Medium, accessed March 31, 2026, [https://medium.com/@unicodeveloper/10-must-have-skills-for-claude-and-any-coding-agent-in-2026-b5451b013051](https://medium.com/@unicodeveloper/10-must-have-skills-for-claude-and-any-coding-agent-in-2026-b5451b013051)  
37. claude-scientific-writer/skills/generate-image/SKILL.md at main \- GitHub, accessed March 31, 2026, [https://github.com/K-Dense-AI/claude-scientific-writer/blob/main/skills/generate-image/SKILL.md](https://github.com/K-Dense-AI/claude-scientific-writer/blob/main/skills/generate-image/SKILL.md)  
38. Effective context engineering for AI agents \- Anthropic, accessed March 31, 2026, [https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)  
39. Pasted images visible to vision but not saveable to filesystem \#39572 \- GitHub, accessed March 31, 2026, [https://github.com/anthropics/claude-code/issues/39572](https://github.com/anthropics/claude-code/issues/39572)  
40. MCP Screenshot Server \- LobeHub, accessed March 31, 2026, [https://lobehub.com/mcp/digital-defiance-mcp-screenshot](https://lobehub.com/mcp/digital-defiance-mcp-screenshot)  
41. Image Analysis MCP Server \- LobeHub, accessed March 31, 2026, [https://lobehub.com/mcp/jfdasher-image-analysis-mcp](https://lobehub.com/mcp/jfdasher-image-analysis-mcp)  
42. How Claude Code works \- Claude Code Docs, accessed March 31, 2026, [https://code.claude.com/docs/en/how-claude-code-works](https://code.claude.com/docs/en/how-claude-code-works)  
43. \[BUG\] Valid PNG images downloaded from GitHub issues cause 'Could not process image' error · Issue \#26788 · anthropics/claude-code, accessed March 31, 2026, [https://github.com/anthropics/claude-code/issues/26788](https://github.com/anthropics/claude-code/issues/26788)  
44. The Claude Code skills actually worth installing right now (March 2026\) \- Reddit, accessed March 31, 2026, [https://www.reddit.com/r/AI\_Agents/comments/1s51cre/the\_claude\_code\_skills\_actually\_worth\_installing/](https://www.reddit.com/r/AI_Agents/comments/1s51cre/the_claude_code_skills_actually_worth_installing/)  
45. Claude API Pricing 2026: Full Anthropic Cost Breakdown \- MetaCTO, accessed March 31, 2026, [https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration)  
46. Gemini 3.1 Pro Cost: Complete 2026 Pricing Guide \- GlobalGPT, accessed March 31, 2026, [https://www.glbgpt.com/hub/gemini-3-1-pro-cost-complete-2026-pricing-guide/](https://www.glbgpt.com/hub/gemini-3-1-pro-cost-complete-2026-pricing-guide/)
