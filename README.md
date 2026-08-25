# Teleportation-QOTP Quantum Signature Experiments and Manuscript

本仓库统一保存论文 **entropy-4455643** 的实验代码、实验结果、IBM Quantum
真机记录、LaTeX 主文件、论文 PDF、正文图件及其数据。仓库按照“实验代码”和
“论文”两部分组织，使论文中的电路、图件和数据能够直接定位到对应实现。

实验覆盖逻辑 Qiskit 电路构建、IBM Aer 模拟器执行和 IBM Quantum 真机执行。
真机结果属于电路正确性与性能证据，不等同于安全概率，也不构成完整的分布式
Alice--Bob--Trent 量子网络部署或形式化安全证明。

## 仓库结构

```text
.
├── README.md
├── requirements.txt
├── experiments/
│   ├── qiskit_simulation/
│   │   ├── code/                       # Qiskit 逻辑电路构建与导出代码
│   │   └── results/                    # 模块及组合线路的 QASM/TXT/PDF/PNG/SVG
│   ├── ibm_aer_simulation/
│   │   ├── code/                       # Aer 后端转译与模拟代码
│   │   └── results/                    # Aer 线路、图件和转译指标
│   └── ibm_hardware/
│       ├── code/                       # IBM Runtime、离线重绘及完整单 QPU 协议核心代码
│       └── results/                    # 真机线路、counts、CSV、job 元数据和正式图件
└── paper/
    ├── manuscript/
    │   ├── Entropygroveralgorithmsignaturev7.tex
    │   ├── Entropygroveralgorithmsignaturev7.pdf
    │   ├── Definitions/                # MDPI 模板与参考文献样式
    │   └── *.sty, *.cls, *.clo, *.bbl # 本地编译依赖
    ├── figures/                        # 论文使用的 PDF/PNG/EPS 图件
    └── data/
        ├── numerical/                  # 数值模拟 CSV、元数据及绘图代码
        └── ibm/                        # IBM/Aer CSV、原始 counts 与运行元数据
```

仓库只保留当前论文主体及其直接相关的实验和可复现材料。旧论文版本、重复交付
压缩包、Word 讲解文件、缓存、虚拟环境和临时编译目录不纳入统一仓库。

## 论文与实验对应关系

| 论文对象 | 代码位置 | 结果或数据位置 |
| --- | --- | --- |
| Bell pair、teleportation、QOTP、swap test 逻辑线路 | `experiments/qiskit_simulation/code/` | `experiments/qiskit_simulation/results/` |
| Aer 转译与模拟线路 | `experiments/ibm_aer_simulation/code/` | `experiments/ibm_aer_simulation/results/` |
| IBM 模块与 staged candidate | `experiments/ibm_hardware/code/IBM_Hardware_Full_Pipeline.py` | `experiments/ibm_hardware/results/*.csv` |
| 23-logical-qubit 单 QPU 协议核心候选 | `experiments/ibm_hardware/code/IBM_Complete_Single_QPU_Protocol.py` | `experiments/ibm_hardware/results/complete_single_qpu_run_20260810/` |
| 数值仿真图 | `paper/data/numerical/Numerical_Simulation_Full_Pipeline.py` | `paper/data/numerical/`, `paper/figures/combined_numerical_simulations.*` |
| IBM 硬件图 | `paper/data/ibm/ibm_hardware_result_figure_code.py` | `paper/data/ibm/`, `paper/figures/combined_ibm_hardware_results.*` |

## Python 环境

建议使用 Python 3.11 或更高版本，并在独立虚拟环境中安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

主要依赖包括 NumPy、pandas、Matplotlib、Qiskit、Qiskit Aer 和
Qiskit IBM Runtime。

## 复现实验

以下命令从仓库根目录运行。

### 1. Qiskit 逻辑电路与图件

```bash
python experiments/qiskit_simulation/code/Qiskit_Circuit_Code.py
```

该入口重新构建模块线路和组合线路，并在
`experiments/qiskit_simulation/results/` 中输出 QASM、文本线路图以及
PDF/PNG/SVG 图件。

### 2. IBM Aer 仿真实验

```bash
python experiments/ibm_aer_simulation/code/Aer_Circuit_Code.py
```

该入口使用固定 transpiler seed 在 AerSimulator 上转译线路，输出 Aer 线路图和
`Aer_Transpilation_Metrics.csv`。

### 3. 已保存 IBM 数据的离线重绘

```bash
python experiments/ibm_hardware/code/IBM_Hardware_Full_Pipeline.py \
  --mode plot-existing \
  --output experiments/ibm_hardware/results/combined_ibm_hardware_results
```

该命令只读取仓库中保存的 CSV，不连接 IBM Quantum，也不会提交新任务。

### 4. 完整单 QPU 协议核心的 Aer 检查

```bash
python experiments/ibm_hardware/code/IBM_Complete_Single_QPU_Protocol.py \
  --mode aer \
  --shots 2048 \
  --output-dir experiments/ibm_hardware/results/local_aer_complete_core
```

在线提交不是复现本仓库结果的必要步骤。如确需连接 IBM Quantum，凭据必须仅由
本地环境变量提供，不得写入代码或 Git：

```bash
export QISKIT_IBM_TOKEN="..."
export QISKIT_IBM_CRN="..."
```

提交模式还要求显式使用 `--confirm-submit`，以避免意外占用真机资源。

## IBM 真机记录

正式四面板硬件图使用已保存的 `ibm_fez` 模块和 staged-candidate 数据，其中：

- Pilot job：`d9o7s1fa5u8s73e2csjg`，128 shots；
- Final job：`d9o7tjva5u8s73e2cv9g`，1024 shots，773/1024 correct outputs。

仓库还保存了一次独立的完整单 QPU 协议核心候选运行：

- Backend：`ibm_marrakesh`；
- Job ID：`d9sn9r9dsedc73ai01g0`；
- Shots：1024；
- 联合判决通过：170/1024。

该 23-logical-qubit 线路在同一 QPU 上使用不同逻辑寄存器表示 Alice、Bob 和
Trent，并组合三份消息、三组 Bell 资源、teleportation、strengthened-QOTP、
两次 swap test 及记录一致性判决。它应称为 **complete single-QPU
protocol-core candidate**，不能称为三个物理节点上的分布式完整协议。

## 编译论文

论文使用 MDPI `entropy` 模板。仓库保留了投稿目录中的主 TeX、对应 PDF、
`Definitions/` 及本地样式依赖。编译命令为：

```bash
cd paper/manuscript
latexmk -pdf Entropygroveralgorithmsignaturev7.tex
```

为保持投稿包可直接编译，正文引用的 PDF/EPS 图件同时保留在
`paper/manuscript/`；其按格式归档的正式副本位于 `paper/figures/`。

## 结果解释范围

- Swap-test 检测概率依赖输入态 fidelity；`2^{-lambda}` 只适用于正交态。
- 数值攻击实验是 targeted benchmark，不代表任意 CPTP 攻击下的普遍安全性。
- Strengthened-QOTP 的平均密文结论支持 confidentiality，不单独提供完整性或
  quantum authentication。
- Aer 和 IBM hardware correct-output probability 是电路性能量，不是协议安全
  概率。
- 单 QPU 协议核心没有实现物理三节点隔离、跨 QPU 量子链路、QKD、认证会话绑定
  或争议仲裁。

## 数据与凭据管理

论文图件所用 CSV 和运行元数据位于 `paper/data/`。真机目录保留 job ID、backend、
shots、QASM、原始 counts 和解析后的 CSV，已有结果可以离线检查而无需再次提交。

仓库不包含 IBM Quantum token、CRN 实际值、GitHub token、私钥或本地 `.env`
文件。凭据只能通过运行环境注入。
