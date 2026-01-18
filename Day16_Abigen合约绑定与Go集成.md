# Day 16: Abigen 合约绑定与 Go 集成

> **学习时间**：4-6 小时（理论 1.5h + 实战 4h + 复习 0.5h）
>
> **核心目标**：掌握使用 `abigen` 生成 Go 合约绑定，实现 Go 程序与智能合约的强类型交互（部署、调用、监听）。

---

## 🎯 今日学习目标

- [ ] 安装并配置 `abigen` 工具
- [ ] 理解 ABI 到 Go 结构体的映射原理
- [ ] 使用 Go 代码部署智能合约
- [ ] 实现合约读取（Call）与写入（Transact）
- [ ] 掌握合约事件监听（Event Listening）

---

## 📚 理论课：Abigen 工作原理

### 1. 什么是 Abigen？

`abigen` 是 `go-ethereum` (Geth) 提供的一个命令行工具，用于将 Solidity 合约编译后的 ABI (Application Binary Interface) 和 Bytecode 转换为 Go 语言的 wrapper代码。

**优势**：
- **类型安全**：自动生成结构体和方法，避免手动解析 ABI 的类型错误。
- **易用性**：像调用本地 Go 函数一样调用链上合约。
- **功能全**：自动封装了部署（Deploy）、绑定（New）、调用（Call/Transact）、过滤（Filter）等方法。

### 2. 生成流程

```mermaid
graph LR
    A[Solidity Source (.sol)] -->|solc| B[ABI & BIN]
    B -->|abigen| C[Go Binding (.go)]
    C -->|Import| D[Go App]
```

### 3. 生成代码结构

生成的 Go 文件通常包含：
- **DeployMyContract**: 部署合约的函数。
- **NewMyContract**: 绑定已部署合约的实例。
- **MyContractSession**: 包含 Auth (TransactOpts) 和 Call (CallOpts) 的会话对象。
- **MyContractCaller/Transactor/Filterer**: 分别对应读、写、事件过滤的底层接口。
- **结构体方法**: 对应 Solidity 中的 public 函数。

---

## 🛠️ 实战作业

### 作业 1：环境准备

#### 1.1 安装 Solidity 编译器 (solc)
```bash
# MacOS
brew update
brew tap ethereum/ethereum
brew install solidity

# 验证
solc --version
```

#### 1.2 安装 Abigen
```bash
# 如果已经安装了 go-ethereum
go install github.com/ethereum/go-ethereum/cmd/abigen@latest

# 验证，确认在 $GOPATH/bin 下
abigen --version
```

### 作业 2：生成绑定文件

#### 2.1 准备 Solidity 合约
使用 Day 12 的 `Counter.sol` 或 Day 13 的 `MyToken.sol`。这里以 `Store.sol` 为例：

```solidity
// Store.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Store {
    event ItemSet(bytes32 indexed key, bytes32 value);

    mapping (bytes32 => bytes32) public items;

    function setItem(bytes32 key, bytes32 value) external {
        items[key] = value;
        emit ItemSet(key, value);
    }

    function getItem(bytes32 key) external view returns (bytes32) {
        return items[key];
    }
}
```

#### 2.2 编译与生成

**方法 A：分步生成**
```bash
# 1. 生成 ABI 和 BIN
solc --abi --bin Store.sol -o build --overwrite

# 2. 生成 Go 文件
abigen --bin=build/Store.bin --abi=build/Store.abi --pkg=store --out=store/Store.go
```

**方法 B：直接生成 (推荐)**
```bash
abigen --sol Store.sol --pkg store --out store/Store.go
```

### 作业 3：Go 集成实战 (Deploy & Interact)

创建一个新的 Go 项目 `day16-go-binding`。

```bash
mkdir day16-go-binding
cd day16-go-binding
go mod init day16
mkdir store
# ... 将生成的 Store.go 放入 store 目录 ...
```

#### 3.1 `main.go` - 连接与部署

```go
package main

import (
	"context"
	"crypto/ecdsa"
	"fmt"
	"log"
	"math/big"

	"day16/store" // 导入生成的包

	"github.com/ethereum/go-ethereum/accounts/abi/bind"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
)

func main() {
    // 1. 连接到 Anvil 本地节点
    client, err := ethclient.Dial("http://127.0.0.1:8545")
    if err != nil {
        log.Fatal(err)
    }

    // 2. 加载私钥 (Anvil 默认账户 0)
    // ⚠️ WARNING: 以下私钥仅用于本地 Anvil 测试，切勿在生产环境使用！
    privateKey, err := crypto.HexToECDSA("ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    if err != nil {
        log.Fatal(err)
    }

    // 3. 创建 TransactOpts (签名器)
    chainID, err := client.ChainID(context.Background())
    if err != nil {
        log.Fatal(err)
    }
    
    auth, err := bind.NewKeyedTransactorWithChainID(privateKey, chainID)
    if err != nil {
        log.Fatal(err)
    }

    // 4. 部署合约
    address, tx, instance, err := store.DeployStore(auth, client)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("合约已部署: %s\n", address.Hex())
    fmt.Printf("部署交易哈希: %s\n", tx.Hash().Hex())
    
    // 等待部署确认...（略，实际项目需等待）
    // 可以在这里简单用 time.Sleep 或 bind.WaitMined
    
    // 5. 写入数据 (Transact)
    key := [32]byte{1}
    value := [32]byte{2}
    copy(key[:], []byte("foo"))
    copy(value[:], []byte("bar"))
    
    tx, err = instance.SetItem(auth, key, value)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("SetItem 交易发送: %s\n", tx.Hash().Hex())

    // 6. 读取数据 (Call)
    // 这里的 nil 是 CallOpts，如果查询历史状态可以指定 BlockNumber
    result, err := instance.GetItem(nil, key)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("GetItem 结果: %s\n", string(result[:])) // 注意去除尾部0
}
```

### 作业 4：事件监听 (Event Subscribing)

Go 客户端可以通过 WebSocket 连接实时监听合约事件。

```go
// event_listener.go
package main

import (
    "fmt"
    "log"
    "day16/store"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/ethclient"
)

func listenEvents() {
    // 必须使用 WebSocket 连接
    client, err := ethclient.Dial("ws://127.0.0.1:8545")
    if err != nil {
        log.Fatal(err)
    }

    // 绑定合约实例 (需要合约地址)
    contractAddress := common.HexToAddress("YOUR_DEPLOYED_ADDRESS")
    instance, err := store.NewStore(contractAddress, client)
    if err != nil {
        log.Fatal(err)
    }

    // 创建 channel 接收事件
    sink := make(chan *store.StoreItemSet)
    
    // 开始订阅 (Start Block, End Block, Filter Params...)
    // WatchItemSet 是 abigen 自动生成的
    sub, err := instance.WatchItemSet(nil, sink, nil) 
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println("开始监听 ItemSet 事件...")

    for {
        select {
        case err := <-sub.Err():
            log.Fatal(err)
        case event := <-sink:
            fmt.Printf("收到新事件! Key: %x, Value: %s\n", event.Key, string(event.Value[:]))
        }
    }
}
```

---

## 📝 知识点总结

### 1. `bind.TransactOpts` vs `bind.CallOpts`

| 选项             | 用途              | 关键字段                              | Gas 消耗      |
| :--------------- | :---------------- | :------------------------------------ | :------------ |
| **TransactOpts** | 写操作 (修改状态) | `From`, `Signer`, `Value`, `GasLimit` | 是 (需要 ETH) |
| **CallOpts**     | 读操作 (查询状态) | `From`, `BlockNumber`, `Context`      | 否 (本地执行) |

### 2. 生成文件解析

- `Deploy[Contract]`: 封装了 ABI 打包、Bytecode 拼接、Nonce 获取、签名、广播全流程。
- `New[Contract]`: 仅在本地创建一个 Go 对象，关联地址和 Client backend，**不发生链上交互**。

### 3. 注意事项
- 部署合约时，`TransactOpts` 的 `Value` 字段对应 `msg.value`（构造函数是否 payable）。
- `Call` 操作默认读取 `Latest` 区块，如果需要读取历史状态，设置 `CallOpts.BlockNumber`。

---

## ✅ 今日检查清单

- [ ] 成功使用 `abigen` 生成了 Go 代码
- [ ] 编写 Go 程序成功连接 Anvil
- [ ] 成功部署合约并获得合约地址
- [ ] 实现了 Set 和 Get 操作
- [ ] (可选) 成功运行 WebSocket 事件监听 demo

---

## 📌 明日预告

**Day 17: Go + Anvil E2E 集成测试**
- 使用 Go Test 测试合约逻辑
- 启动临时的 Anvil 实例进行测试
- 模拟多用户交互场景
- 自动化 CI/CD 流程初探
