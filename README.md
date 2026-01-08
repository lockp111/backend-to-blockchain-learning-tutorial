# 区块链后端开发培训课程（37天）

[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?style=flat-square&logo=go)](https://golang.org/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.x-363636?style=flat-square&logo=solidity)](https://soliditylang.org/)
[![Foundry](https://img.shields.io/badge/Foundry-Latest-DEA584?style=flat-square)](https://book.getfoundry.sh/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> 🎯 **目标人群**：具备扎实 Golang 服务端开发经验，理解数据库、网络、分布式系统基础，但零区块链经验的开发者。

## 📖 课程简介

这是一个为期 **37 天**的密集实战课程，帮助后端开发者快速掌握 **Bitcoin + EVM 双技术栈**，具备支付系统、资产托管、DeFi 应用、跨链开发的能力。

### 技术栈

| 领域         | 技术                            |
| ------------ | ------------------------------- |
| **智能合约** | Solidity + Foundry              |
| **后端服务** | Golang (go-ethereum / btcsuite) |
| **数据库**   | MySQL/PostgreSQL + Redis        |
| **AI 辅助**  | Cursor / Windsurf               |

---

## 🗺️ 课程概览

```mermaid
mindmap
  root((37天区块链全栈课程))
    Week1[Week 1: Bitcoin 核心]
      Day1[区块链基础]
      Day2[密码学与钱包]
      Day3[UTXO 模型]
      Day4[PSBT 多签]
      Day5[时间锁]
      Day6[支付系统]
      Day7[Mini Project]
    Week2[Week 2: 闪电网络 + EVM]
      Day8_10[闪电网络 LND]
      Day11_12[以太坊 + Foundry]
      Day13[Solidity 基础]
      Day14[Week 2 整合]
    Week3[Week 3: 合约进阶]
      Day15[ABI 与 Proxy]
      Day16[Abigen 绑定]
      Day17[E2E 测试]
      Day18_19[Custom Indexer]
      Day20_21[Week 3 整合]
    Week4[Week 4: 资产与 DeFi]
      Day22_23[Merkle Tree]
      Day24_25[Token 标准]
      Day26_27[ERC-4337 AA]
      Day28_29[DeFi 协议]
      Day30[Week 4 整合]
    Week5[Week 5: 安全与跨链]
      Day31_32[资产托管]
      Day33_34[跨链 L2]
      Day35[安全合规]
      Day36_37[结业项目]
```

---

## 🔗 知识图谱

### 核心概念关系

```mermaid
flowchart TB
    subgraph Cryptography["🔐 密码学基础"]
        ECDSA["ECDSA secp256k1"]
        SHA256["SHA-256"]
        Keccak["Keccak-256"]
        BIP39["BIP-39 助记词"]
        BIP32["BIP-32/44 HD钱包"]
    end

    subgraph Bitcoin["₿ Bitcoin 技术栈"]
        UTXO["UTXO 模型"]
        Script["Bitcoin Script"]
        PSBT["PSBT BIP-174"]
        Timelock["时间锁"]
        LN["闪电网络"]
        HTLC["HTLC"]
    end

    subgraph Ethereum["⟠ Ethereum 技术栈"]
        Account["Account 模型"]
        EVM["EVM 虚拟机"]
        Solidity["Solidity"]
        ABI["ABI 编码"]
        Proxy["Proxy 代理"]
    end

    subgraph Standards["📋 资产标准"]
        ERC20["ERC-20"]
        ERC721["ERC-721 NFT"]
        Permit["EIP-2612 Permit"]
        AA["ERC-4337 AA"]
    end

    subgraph DeFi["💰 DeFi 协议"]
        Uniswap["Uniswap V3"]
        Aave["Aave 借贷"]
    end

    ECDSA --> BIP32
    BIP39 --> BIP32
    BIP32 --> UTXO
    BIP32 --> Account
    SHA256 --> UTXO
    Keccak --> Account

    UTXO --> Script --> PSBT
    Script --> Timelock --> HTLC --> LN

    Account --> EVM --> Solidity --> ABI
    Solidity --> Proxy
    ABI --> ERC20 --> Permit
    ERC20 --> Uniswap
    AA --> Permit
    ABI --> ERC721
```

### 学习路径依赖

```mermaid
flowchart TD
    subgraph Phase1["🟢 Phase 1: 基础 (Week 1)"]
        A1["区块链概念"] --> A2["密码学基础"]
        A2 --> A3["UTXO 模型"]
        A3 --> A4["PSBT/多签"]
        A4 --> A5["时间锁"]
        A5 --> A6["支付系统"]
    end

    subgraph Phase2["🔵 Phase 2: 扩展 (Week 2)"]
        B1["闪电网络"] --> B2["以太坊基础"]
        B2 --> B3["Foundry"]
        B3 --> B4["Solidity"]
    end

    subgraph Phase3["🟡 Phase 3: 集成 (Week 3)"]
        C1["ABI/Proxy"] --> C2["Abigen"]
        C2 --> C3["E2E 测试"]
        C3 --> C4["Indexer"]
    end

    subgraph Phase4["🟠 Phase 4: 应用 (Week 4)"]
        D1["Merkle Tree"] --> D2["Token 标准"]
        D2 --> D3["ERC-4337"]
        D3 --> D4["DeFi"]
    end

    subgraph Phase5["🔴 Phase 5: 进阶 (Week 5)"]
        E1["冷热分离"] --> E2["跨链/L2"]
        E2 --> E3["安全审计"]
        E3 --> E4["结业项目"]
    end

    A6 --> B1
    A5 --> B1
    A4 --> E1
    B4 --> C1
    C4 --> D1
    D4 --> E2
```

### 技术栈分层

```mermaid
flowchart LR
    subgraph L1["Layer 1 基础链"]
        BTC["Bitcoin"]
        ETH["Ethereum"]
    end

    subgraph L2["Layer 2 扩展"]
        Lightning["闪电网络"]
        Optimism["Optimism"]
        Arbitrum["Arbitrum"]
    end

    subgraph Backend["Go 后端服务"]
        GoETH["go-ethereum"]
        btcsuite["btcsuite"]
        LNDClient["LND gRPC"]
    end

    subgraph Contract["智能合约"]
        Foundry["Foundry"]
        OZ["OpenZeppelin"]
    end

    BTC --> btcsuite
    BTC --> Lightning --> LNDClient
    ETH --> GoETH --> Foundry
    ETH --> Optimism
    ETH --> Arbitrum
    Foundry --> OZ
```

---

## 📚 课程内容

| Week       | 主题               | 核心技术                         | Day   |
| ---------- | ------------------ | -------------------------------- | ----- |
| **Week 1** | Bitcoin 核心       | UTXO, PSBT, 时间锁, 支付系统     | 1-7   |
| **Week 2** | 闪电网络 + EVM     | LND, Ethereum, Foundry, Solidity | 8-14  |
| **Week 3** | 合约进阶与 Go 集成 | ABI, Abigen, E2E 测试, Indexer   | 15-21 |
| **Week 4** | 资产标准与 DeFi    | Merkle, ERC-4337, Uniswap, Aave  | 22-30 |
| **Week 5** | 安全与跨链         | 冷热分离, L2, MEV, 结业项目      | 31-37 |

### 详细课程文件

- [Day 1: 区块链核心概念](./Day01_区块链核心概念.md)
- [Day 2: 密码学基础与钱包原理](./Day02_密码学基础与钱包原理.md)
- [Day 3: Bitcoin UTXO 模型详解](./Day03_Bitcoin_UTXO模型详解.md)
- [Day 4: PSBT 多方协同](./Day04_PSBT多方协同.md)
- [Day 5: Bitcoin 时间锁](./Day05_Bitcoin时间锁.md)
- [Day 6: Bitcoin 支付系统开发](./Day06_Bitcoin支付系统开发.md)
- [Day 7: Week 1 复习与 Mini Project](./Day07_Week1_复习与_Mini_Project.md)

---

## 🛠️ 工具链生态

```mermaid
flowchart LR
    subgraph Contract["合约开发"]
        Foundry2["Foundry"]
        Forge2["forge test"]
        Cast2["cast call"]
        Anvil2["anvil"]
    end

    subgraph GoBackend["Go 后端"]
        geth["go-ethereum"]
        btc["btcsuite"]
        lnd["lnd/lnrpc"]
        abigen2["abigen"]
    end

    subgraph Infra["基础设施"]
        MySQL["MySQL/PostgreSQL"]
        Redis["Redis"]
    end

    Foundry2 --> Forge2
    Foundry2 --> Cast2
    Foundry2 --> Anvil2
    Foundry2 --> abigen2
    
    abigen2 --> geth
    geth --> MySQL
    btc --> Redis
    lnd --> Redis
```

---

## 📋 核心技术点索引

| 类别         | 技术点                  | Day       | 前置知识 |
| ------------ | ----------------------- | --------- | -------- |
| **密码学**   | ECDSA / BIP-39 / BIP-32 | Day 2     | -        |
| **Bitcoin**  | UTXO / Coin Selection   | Day 3     | 密码学   |
| **Bitcoin**  | PSBT / 多签             | Day 4     | UTXO     |
| **Bitcoin**  | CLTV / CSV 时间锁       | Day 5     | Script   |
| **Bitcoin**  | 支付系统 / Reorg        | Day 6     | RPC      |
| **闪电网络** | 支付通道 / HTLC         | Day 8-10  | 时间锁   |
| **Ethereum** | Account / EVM           | Day 11    | -        |
| **Solidity** | ERC-20 / Fuzzing        | Day 13    | EVM      |
| **Solidity** | ABI / Proxy             | Day 15    | Solidity |
| **Go 集成**  | Abigen / Indexer        | Day 16-19 | ABI      |
| **Merkle**   | Merkle Tree / Proof     | Day 22-23 | 哈希     |
| **标准**     | ERC-4337                | Day 26-27 | Permit   |
| **DeFi**     | Uniswap / Aave          | Day 28-29 | ERC-20   |
| **安全**     | 冷热分离 / MEV          | Day 31-35 | 多签     |

---

## 🚀 快速开始

### 环境要求

```bash
# Go 1.21+
go version

# Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# 验证安装
forge --version
cast --version
anvil --version
```

### 创建第一个项目

```bash
# 创建课程目录
mkdir -p ~/blockchain-course
cd ~/blockchain-course

# 初始化 Go 模块
go mod init blockchain-course

# 安装依赖
go get github.com/btcsuite/btcd
go get github.com/ethereum/go-ethereum

# 初始化 Foundry 项目
forge init contracts
```

---

## 📖 参考资源

### 官方文档
- [Foundry Book (中文版)](https://book.getfoundry.sh/)
- [go-ethereum Wiki](https://geth.ethereum.org/docs)
- [btcsuite Documentation](https://github.com/btcsuite/btcd)

### 标准规范
- [Bitcoin BIPs](https://github.com/bitcoin/bips)
- [Ethereum EIPs](https://eips.ethereum.org/)
- [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337)

### 进阶阅读
- [Paradigm Engineering Blog](https://www.paradigm.xyz/blog)
- [Flashbots Docs](https://docs.flashbots.net/)

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件
