# Day 17: Go + Anvil E2E 集成测试

> **学习时间**：4-6 小时（理论 1h + 实战 4h + 复习 1h）
>
> **核心目标**：构建生产级的 E2E 测试框架，掌握使用 Go 配合 Anvil 本地节点进行全链路合约交互测试。

---

## 🎯 今日学习目标

- [ ] 理解 E2E 测试 vs 单元测试的区别
- [ ] 掌握在 Go 测试中启动和管理 Anvil 进程
- [ ] 实现测试环境的快速重置（Snapshot/Revert）
- [ ] 编写复杂的用户交互场景测试
- [ ] 集成 GitHub Actions CI 流程

---

## 📚 理论课：测试金字塔与 E2E

### 1. 为什么需要 E2E 测试？

虽然 Solidity (Foundry) 单元测试非常强大，但它无法覆盖链下业务逻辑。E2E 测试关注的是**前端/后端 + 区块链**的整体集成。

| 测试类型       | 工具               | 关注点           | 优势              | 劣势           |
| :------------- | :----------------- | :--------------- | :---------------- | :------------- |
| **单元测试**   | Foundry (Solidity) | 合约内部逻辑     | 极快、覆盖率高    | 无法测后端集成 |
| **集成测试**   | Go + Anvil         | 合约 + Go SDK    | 模拟真实 RPC 交互 | 较慢           |
| **端到端测试** | Cypress/Playwright | 前端 + 后端 + 链 | 模拟真实用户      | 最慢、最脆弱   |

### 2. Anvil：完美的测试伴侣

Anvil (Foundry 工具套件) 是一个极速的本地以太坊节点，专为测试设计。

**关键特性**：
- **极速启动**：毫秒级启动。
- **作弊码 (Cheatcodes)**：支持 `vm.warp`, `vm.roll` 等（通过 RPC）。
- **状态快照**：`evm_snapshot` 和 `evm_revert` 允许在测试用例之间瞬间重置状态，无需重启节点。

---

## 🛠️ 实战作业

### 作业 1：构建测试脚手架

创建一个 Go 测试助手，用于自动启动和关闭 Anvil。

```go
// test_helper.go
package main_test

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/ethereum/go-ethereum/rpc"
)

const (
    AnvilPort = "8545"
    AnvilURL  = "http://127.0.0.1:" + AnvilPort
)

// TestEnv 包含测试环境上下文
type TestEnv struct {
    Cmd       *exec.Cmd
    Client    *ethclient.Client
    RpcClient *rpc.Client
    Snapshot  string
}

// SetupAnvil 启动 Anvil 并在测试结束时关闭
func SetupAnvil(t *testing.T) *TestEnv {
    // 1. 启动 Anvil 进程
    cmd := exec.Command("anvil", "--port", AnvilPort, "--block-time", "1")
    if err := cmd.Start(); err != nil {
        t.Fatalf("无法启动 Anvil: %v", err)
    }

    // 2. 注册清理函数 (无论测试成功失败都会执行)
    t.Cleanup(func() {
        if err := cmd.Process.Kill(); err != nil {
            t.Logf("无法关闭 Anvil: %v", err)
        }
        cmd.Wait()
    })

    // 3. 等待 Anvil就绪
    // 简单轮询检查端口是否可达，或直接等待 1-2 秒
    time.Sleep(1 * time.Second)

    // 4. 连接客户端
    rpcClient, err := rpc.Dial(AnvilURL)
    if err != nil {
        t.Fatalf("RPC连接失败: %v", err)
    }
    
    client := ethclient.NewClient(rpcClient)

    return &TestEnv{
        Cmd:       cmd,
        Client:    client,
        RpcClient: rpcClient,
    }
}
```

### 作业 2：实现状态重置 (Snapshot/Revert)

为了保证每个测试用例互不干扰，我们使用 Snapshot 机制。

```go
// Reset 将链状态回滚到初始快照
func (e *TestEnv) SnapshotState(t *testing.T) {
    err := e.RpcClient.Call(&e.Snapshot, "evm_snapshot")
    if err != nil {
        t.Fatalf("创建快照失败: %v", err)
    }
}

func (e *TestEnv) RevertState(t *testing.T) {
    var result bool
    err := e.RpcClient.Call(&result, "evm_revert", e.Snapshot)
    if err != nil || !result {
        t.Fatalf("回滚状态失败: %v", err)
    }
    // 回滚后需要重新创建新的快照，因为旧快照ID会失效
    e.SnapshotState(t)
}
```

### 作业 3：编写集成测试用例

假设我们已经在 Day 16 生成了 `store` 合约的绑定。

```go
// store_test.go
package main_test

import (
	"context"
	"math/big"
	"testing"
    "day16/store" // 引用 Day 16 生成的包

	"github.com/ethereum/go-ethereum/accounts/abi/bind"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

// Anvil 默认私钥 (Account 0)
// 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
var (
    DeployerKey, _ = crypto.HexToECDSA("ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
)

func TestStoreFlow(t *testing.T) {
    env := SetupAnvil(t)
    
    // 初始化 Auth
    auth, _ := bind.NewKeyedTransactorWithChainID(DeployerKey, big.NewInt(31337)) // Anvil ChainID
    
    // 1. 部署合约
    address, _, instance, err := store.DeployStore(auth, env.Client)
    if err != nil {
        t.Fatalf("部署失败: %v", err)
    }
    t.Logf("合约部署于: %s", address.Hex())
    
    // 创建快照 (此后的修改都可以回滚)
    env.SnapshotState(t)

    t.Run("应该能够通过部署者设置值", func(t *testing.T) {
        defer env.RevertState(t) // 测试结束后回滚

        key := [32]byte{1}
        val := [32]byte{0xAA}
        
        // 发送交易
        tx, err := instance.SetItem(auth, key, val)
        if err != nil {
            t.Fatalf("SetItem 失败: %v", err)
        }

        // 等待挖矿 (Anvil 默认自动挖矿，但 Go 客户端需要等待回执)
        receipt, err := bind.WaitMined(context.Background(), env.Client, tx)
        if err != nil {
            t.Fatalf("等待挖矿失败: %v", err)
        }
        if receipt.Status != 1 {
            t.Fatal("交易执行失败")
        }

        // 验证状态
        res, _ := instance.GetItem(nil, key)
        if res != val {
            t.Errorf("期望 %x, 得到 %x", val, res)
        }
    })

    t.Run("未设置的值应为空", func(t *testing.T) {
        defer env.RevertState(t)
        
        // 由于回滚了，之前的状态应该不存在
        key := [32]byte{1}
        res, _ := instance.GetItem(nil, key)
        var empty [32]byte
        if res != empty {
            t.Error("状态未正确回滚")
        }
    })
}
```

### 作业 4：GitHub Actions 集成

创建 `.github/workflows/test.yml`，在 CI 中自动运行这些测试。

```yaml
name: Go E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Foundry (for Anvil)
        uses: foundry-rs/foundry-toolchain@v1
        
      - name: Install Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'
          
      - name: Run Tests
        run: go test -v ./...
```

---

## 📝 知识点总结

### 1. `evm_snapshot` vs `evm_revert`
Anvil 独有的 RPC 方法，非常适合测试。
- `snapshot`: 保存当前完整的 EVM 状态，返回一个 ID。
- `revert`: 接受一个 ID，将整个链状态（包括区块高度、余额、存储）瞬间恢复到该快照时刻。

### 2. 对比 Geth Dev Mode
- Geth 也可以运行 Dev 模式，但启动较慢，且不支持 `evm_revert` 这种作弊码。
- Anvil 是基于 Rust 的，启动和执行速度通常是 Geth 的 10 倍以上。

### 3. 测试隔离原则
- 每个 `t.Run` 子测试都应该在一个干净的环境中运行。
- 在 `Setup` 阶段创建快照，在 `defer` 中执行回滚，是实现测试隔离的最佳实践。

---

## ✅ 今日检查清单

- [ ] 成功编写 `SetupAnvil` 辅助函数
- [ ] 理解并实现了 Snapsho/Revert 机制
- [ ] 编写了一个包含部署、状态修改、状态验证的完整测试
- [ ] 验证了 `t.Run` 之间的状态是隔离的
- [ ] 配置了 CI 脚本 (可在本地模拟验证)

---

## 📌 明日预告

**Day 18: 高性能事件监听与 Custom Indexer (Part 1)**
- 为什么直接 `eth_getLogs` 不够好？
- 处理区块重组 (Reorg)
- 构建可靠的事件摄取器 (Ingester)
