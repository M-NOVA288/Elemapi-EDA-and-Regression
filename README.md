# Python Projects: Reliability Tooling, Data and Machine Learning

| Project | What it shows |
|---|---|
| [**02 – SLO & Log Analyzer**](02-slo-log-analyzer) | SRE tooling: SLO / error-budget reporting, multiwindow burn-rate alert replay, anomaly detection on log data. Standard-library Python, 13 tests, CI. |
| [**Cat vs. Dog & MNIST classifiers**](Cat_Dog_Classification) | Deep learning in TensorFlow/Keras (Colab notebooks): a CNN with a custom rotation-augmentation function compared across learning rates, and a fully connected MNIST network with L2 regularization, dropout, early stopping and checkpointing. |
| [**01 – Inventory CLI**](01-inventory-system) | Python + SQLite command-line app with parameterized queries. |
| [Course snippets](COURSE:SPECIAL_TOPICS_IN_COMPUTERSCIENCE_DEEPLEARNING&NEURALNETWORKS) | Short examples from a deep learning course (PyTorch model definition, scikit-learn text features). |

The SLO analyzer is built to read the structured logs from my
[Deal Liaison](https://github.com/M-NOVA288/Deal-liaison-w-Vercel-Supabase) service and complements the
failure-handling work in [VoxBook](https://github.com/M-NOVA288/Vox-book-engine).

```bash
cd 02-slo-log-analyzer && python -m slo_toolkit report data/sample_logs.jsonl
```
