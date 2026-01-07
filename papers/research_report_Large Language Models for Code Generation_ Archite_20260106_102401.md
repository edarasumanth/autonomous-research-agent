# Research Report: Large Language Models for Code Generation: Architectures, Training Approaches, and Evaluation Benchmarks

*Generated: 2026-01-06 10:24:01*

---

## Executive Summary

Large Language Models (LLMs) have revolutionized automated code generation, enabling the transformation of natural language descriptions into functional source code. This research overview examines the current landscape of code LLMs, focusing on key architectures, training methodologies, and evaluation benchmarks from 2023-2024.

The field has seen remarkable progress with both proprietary models (GPT-4, Codex) and open-source alternatives (Code Llama, StarCoder, DeepSeek-Coder) achieving impressive results. Code Llama, released by Meta AI, represents a significant milestone as an open foundation model, achieving up to 67.8% pass@1 on HumanEval with its instruction-tuned 70B variant. Key training innovations include initialization from general-purpose LLMs, code-heavy dataset curation (85%+ code), fill-in-the-middle (FIM) objectives for infilling capabilities, and long context fine-tuning enabling processing of up to 100,000 tokens.

Evaluation of code generation models primarily relies on benchmarks like HumanEval (164 function-level tasks) and MBPP (974 tasks), using the pass@k metric to measure functional correctness. However, critical reviews highlight that current benchmarks may not fully reflect real-world usability, and syntactic similarity metrics like BLEU have been shown to correlate poorly with actual code correctness. The field continues to evolve with emerging focus areas including repository-level code generation, retrieval-augmented approaches, and autonomous coding agents.

---

## Key Findings

1. Code LLMs can be categorized into three architectural types: encoder-only (CodeBERT) for comprehension, decoder-only (StarCoder, CodeGen, Code Llama) for generation tasks, and encoder-decoder (CodeT5) for both.

2. Initializing code LLMs from pretrained general-purpose models significantly outperforms training from scratch - Code Llama initialized from Llama 2 required ~240B fewer tokens to achieve equivalent performance.

3. Code Llama - Instruct 70B achieves 67.8% pass@1 on HumanEval, matching GPT-4's performance among open-source models.

4. Training data composition typically uses 85%+ code with 7-8% natural language, and including discussions about code improves benchmark performance.

5. Fill-in-the-middle (FIM) training enables IDE code completion with only modest performance cost (~0.6-1.1% points on standard benchmarks).

6. Long context fine-tuning via RoPE position embedding modification enables processing up to 100,000 tokens with stable behavior.

7. Self-instruct methods using execution feedback (generating problems, tests, solutions, then filtering by test passage) significantly improve instruction-following capabilities.

8. HumanEval (164 tasks) and MBPP (974 tasks) are the primary benchmarks, but they may not reflect real-world coding scenarios.

9. The pass@k metric measures probability of generating at least one correct solution in k trials, but doesn't reflect actual user workflows.

10. BLEU and similar syntactic metrics fail to assess functional correctness and are inversely correlated with actual code quality.

11. Emerging research areas include repository-level code generation, retrieval-augmented generation, and autonomous coding agents like Devin.


---

## Paper Summaries

### Code Llama: Open Foundation Models for Code (Rozière et al., 2023)

**Source:** arXiv:2308.12950

Meta AI's family of code LLMs based on Llama 2, offering three variants (base, Python-specialized, instruction-tuned) in 7B-70B sizes. Key innovations include infilling capabilities via FIM training, long context support up to 100k tokens, and self-instruct training with execution feedback. Achieves state-of-the-art among open models on HumanEval (67.8% for Instruct-70B) and MultiPL-E benchmarks.

### A Survey on Large Language Models for Code Generation (Jiang et al., 2024)

**Source:** arXiv:2406.00515

Comprehensive survey covering the full landscape of code LLMs including architectures (encoder-only, decoder-only, encoder-decoder), training pipelines (pre-training, fine-tuning, RLHF alignment), and advanced topics like retrieval-augmented generation and autonomous coding agents. Documents the evolution from Codex (2021) through Code Llama (2023) to StarCoder2 and CodeGemma (2024).

### Benchmarks and Metrics for Evaluations of Code Generation: A Critical Review (Ghosh Paul et al., 2024)

**Source:** arXiv:2406.12655

Critical analysis of evaluation methods for code generation. Reviews major benchmarks (HumanEval, MBPP, APPS, ClassEval, CoderEval) and metrics (pass@k, BLEU, CodeBLEU). Key finding: syntactic similarity metrics poorly correlate with functional correctness, and pass@k doesn't reflect real usability. Identifies need for metrics that better capture practical usefulness.


---

## Research Methodology

This quick overview research was conducted using systematic web searches across academic databases focusing on LLMs for code generation from 2023-2024. Three search queries were executed targeting: (1) key models like Codex, CodeLlama, and StarCoder, (2) evaluation benchmarks including HumanEval, and (3) training approaches and datasets. Three highly relevant papers were downloaded and analyzed: the Code Llama technical paper from Meta AI, a comprehensive 2024 survey on LLMs for code generation, and a critical review of benchmarks and metrics. Key findings, paper summaries, and insights were documented and synthesized into this report.


---

## References

1. Rozière, B., et al. (2023). Code Llama: Open Foundation Models for Code. arXiv:2308.12950
2. Jiang, J., et al. (2024). A Survey on Large Language Models for Code Generation. arXiv:2406.00515
3. Ghosh Paul, D., Zhu, H., & Bayley, I. (2024). Benchmarks and Metrics for Evaluations of Code Generation: A Critical Review. arXiv:2406.12655
4. Chen, M., et al. (2021). Evaluating Large Language Models Trained on Code (Codex). arXiv:2107.03374
5. Li, R., et al. (2023). StarCoder: May the source be with you! arXiv:2305.06161
6. Nijkamp, E., et al. (2023). CodeGen: An Open Large Language Model for Code with Multi-Turn Program Synthesis. ICLR 2023
7. Touvron, H., et al. (2023). Llama 2: Open Foundation and Fine-Tuned Chat Models. arXiv:2307.09288



---

*Generated by Autonomous Research Agent*