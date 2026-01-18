# Day 11: 以太坊交易与 Go 客户端开发

> **学习时间**：4-6 小时（理论 1.5h + 实战 3-4h + 复习 0.5h）
>
> **核心目标**：掌握以太坊交易构造、签名与发送，实现生产级的客户端封装

---

## 🎯 今日学习目标

- [ ] 掌握交易构造与签名流程（EIP-155/EIP-1559）
- [ ] 理解 Nonce 管理的重要性与并发处理
- [ ] 实现 Gas 估算与 EIP-1559 费用计算
- [ ] 掌握 Multicall 批量调用优化
- [ ] 实现 Rate Limiting 流控与 Failover 机制

---

## 📚 理论课：交易生命周期

### 交易构造流程

![Transaction Flow](assets/day11/tx_flow.png)

---

### Nonce 管理

#### 为什么 Nonce 很重要？

```
┌────────────────────────────────────────────────────────────────┐
│                       Nonce 机制                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Nonce = 账户已发送的交易数量（从 0 开始）                       │
│                                                                │
│  作用：                                                        │
│  1. 防止交易重放攻击                                           │
│  2. 保证交易顺序执行                                           │
│  3. 允许交易替换（相同 Nonce，更高 Gas）                        │
│                                                                │
│  规则：                                                        │
│  • Nonce 必须严格递增                                          │
│  • Nonce = 当前值才能被打包                                    │
│  • 跳过的 Nonce 会阻塞后续交易                                 │
│                                                                │
│  示例：                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 账户当前 Nonce: 5                                       │   │
│  │                                                         │   │
│  │ 发送 Nonce=5 ✓ → 被打包，账户 Nonce 变为 6              │   │
│  │ 发送 Nonce=7 ✗ → 卡在 Mempool，等待 Nonce=6             │   │
│  │ 发送 Nonce=5 ✗ → 交易被拒绝（Nonce 太低）               │   │
│  │ 发送 Nonce=6 (更高 Gas) → 替换 Mempool 中的 Nonce=6     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### 并发场景的 Nonce 问题

```
┌────────────────────────────────────────────────────────────────┐
│                    并发 Nonce 冲突                              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  问题场景：多个服务同时发送交易                                  │
│                                                                │
│  服务 A ─┬─→ 查询 Nonce (得到 5)                               │
│          │                                                     │
│  服务 B ─┼─→ 查询 Nonce (得到 5)  ← 同时查询！                  │
│          │                                                     │
│  服务 A ─┼─→ 发送 Nonce=5 ✓                                    │
│          │                                                     │
│  服务 B ─┴─→ 发送 Nonce=5 ✗  ← 冲突！                          │
│                                                                │
│  解决方案：                                                    │
│  1. 本地 Nonce 管理器（内存计数 + 原子操作）                    │
│  2. Redis 分布式锁 + Nonce 缓存                                │
│  3. 使用 PendingNonce (考虑未确认交易)                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

### Multicall 优化

#### 为什么需要 Multicall？

```
┌────────────────────────────────────────────────────────────────┐
│                    Multicall 批量调用                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  问题：查询 100 个代币余额                                      │
│                                                                │
│  传统方式：100 次 RPC 调用                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  for token in tokens:                                    │  │
│  │      balance = eth_call(token.balanceOf(user))           │  │
│  │                                                          │  │
│  │  • 100 次网络往返                                         │  │
│  │  • 容易触发 Rate Limit                                   │  │
│  │  • 延迟高                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Multicall 方式：1 次 RPC 调用                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  calls = [token.balanceOf(user) for token in tokens]     │  │
│  │  results = Multicall.aggregate(calls)                    │  │
│  │                                                          │  │
│  │  • 1 次网络往返                                          │  │
│  │  • 避免 Rate Limit                                       │  │
│  │  • 延迟低                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Multicall 合约地址（主网）：                                   │
│  Multicall3: 0xcA11bde05977b3631167028862bE2a173976CA11          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 实战作业

### 作业 1：交易签名与发送

#### 1.1 钱包管理

```go
// wallet/wallet.go
package wallet

import (
    "crypto/ecdsa"
    "fmt"
    "math/big"
    
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/crypto"
)

// Wallet 以太坊钱包
type Wallet struct {
    privateKey *ecdsa.PrivateKey
    publicKey  *ecdsa.PublicKey
    address    common.Address
}

// NewWalletFromPrivateKey 从私钥创建钱包
func NewWalletFromPrivateKey(privateKeyHex string) (*Wallet, error) {
    // 移除 0x 前缀
    if len(privateKeyHex) > 2 && privateKeyHex[:2] == "0x" {
        privateKeyHex = privateKeyHex[2:]
    }
    
    privateKey, err := crypto.HexToECDSA(privateKeyHex)
    if err != nil {
        return nil, fmt.Errorf("无效的私钥: %w", err)
    }
    
    publicKey := privateKey.Public().(*ecdsa.PublicKey)
    address := crypto.PubkeyToAddress(*publicKey)
    
    return &Wallet{
        privateKey: privateKey,
        publicKey:  publicKey,
        address:    address,
    }, nil
}

// GenerateWallet 生成新钱包
func GenerateWallet() (*Wallet, error) {
    privateKey, err := crypto.GenerateKey()
    if err != nil {
        return nil, err
    }
    
    publicKey := privateKey.Public().(*ecdsa.PublicKey)
    address := crypto.PubkeyToAddress(*publicKey)
    
    return &Wallet{
        privateKey: privateKey,
        publicKey:  publicKey,
        address:    address,
    }, nil
}

// Address 获取地址
func (w *Wallet) Address() common.Address {
    return w.address
}

// PrivateKey 获取私钥（谨慎使用）
func (w *Wallet) PrivateKey() *ecdsa.PrivateKey {
    return w.privateKey
}

// PrivateKeyHex 获取私钥十六进制
func (w *Wallet) PrivateKeyHex() string {
    return fmt.Sprintf("%x", crypto.FromECDSA(w.privateKey))
}
```

#### 1.2 交易构造与发送

```go
// transaction/tx_builder.go
package transaction

import (
    "context"
    "fmt"
    "math/big"
    
    "github.com/ethereum/go-ethereum"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/core/types"
    "github.com/ethereum/go-ethereum/ethclient"
)

// TxBuilder 交易构造器
type TxBuilder struct {
    client  *ethclient.Client
    chainID *big.Int
}

// NewTxBuilder 创建交易构造器
func NewTxBuilder(client *ethclient.Client, chainID *big.Int) *TxBuilder {
    return &TxBuilder{
        client:  client,
        chainID: chainID,
    }
}

// BuildLegacyTx 构造 Legacy 交易
func (b *TxBuilder) BuildLegacyTx(ctx context.Context, 
    from, to common.Address, 
    value *big.Int, 
    data []byte) (*types.Transaction, error) {
    
    // 获取 Nonce
    nonce, err := b.client.PendingNonceAt(ctx, from)
    if err != nil {
        return nil, fmt.Errorf("获取 nonce 失败: %w", err)
    }
    
    // 估算 Gas
    gasLimit, err := b.estimateGas(ctx, from, to, value, data)
    if err != nil {
        return nil, fmt.Errorf("估算 gas 失败: %w", err)
    }
    
    // 获取 Gas Price
    gasPrice, err := b.client.SuggestGasPrice(ctx)
    if err != nil {
        return nil, fmt.Errorf("获取 gas price 失败: %w", err)
    }
    
    // 构造交易
    tx := types.NewTransaction(nonce, to, value, gasLimit, gasPrice, data)
    return tx, nil
}

// BuildEIP1559Tx 构造 EIP-1559 交易
func (b *TxBuilder) BuildEIP1559Tx(ctx context.Context,
    from, to common.Address,
    value *big.Int,
    data []byte) (*types.Transaction, error) {
    
    // 获取 Nonce
    nonce, err := b.client.PendingNonceAt(ctx, from)
    if err != nil {
        return nil, fmt.Errorf("获取 nonce 失败: %w", err)
    }
    
    // 估算 Gas
    gasLimit, err := b.estimateGas(ctx, from, to, value, data)
    if err != nil {
        return nil, fmt.Errorf("估算 gas 失败: %w", err)
    }
    
    // 获取基础费用
    header, err := b.client.HeaderByNumber(ctx, nil)
    if err != nil {
        return nil, fmt.Errorf("获取区块头失败: %w", err)
    }
    
    // 获取建议的小费
    gasTipCap, err := b.client.SuggestGasTipCap(ctx)
    if err != nil {
        return nil, fmt.Errorf("获取 tip cap 失败: %w", err)
    }
    
    // 计算最大费用 = 2 * baseFee + tip
    gasFeeCap := new(big.Int).Mul(header.BaseFee, big.NewInt(2))
    gasFeeCap.Add(gasFeeCap, gasTipCap)
    
    // 构造 EIP-1559 交易
    tx := types.NewTx(&types.DynamicFeeTx{
        ChainID:   b.chainID,
        Nonce:     nonce,
        GasTipCap: gasTipCap,
        GasFeeCap: gasFeeCap,
        Gas:       gasLimit,
        To:        &to,
        Value:     value,
        Data:      data,
    })
    
    return tx, nil
}

// estimateGas 估算 Gas
func (b *TxBuilder) estimateGas(ctx context.Context,
    from, to common.Address,
    value *big.Int,
    data []byte) (uint64, error) {
    
    msg := ethereum.CallMsg{
        From:  from,
        To:    &to,
        Value: value,
        Data:  data,
    }
    
    gas, err := b.client.EstimateGas(ctx, msg)
    if err != nil {
        return 0, err
    }
    
    // 增加 20% 缓冲
    return gas * 120 / 100, nil
}
```

#### 1.3 签名与广播

```go
// transaction/signer.go
package transaction

import (
    "context"
    "crypto/ecdsa"
    "fmt"
    "math/big"
    "time"
    
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/core/types"
    "github.com/ethereum/go-ethereum/ethclient"
)

// Signer 交易签名器
type Signer struct {
    client  *ethclient.Client
    chainID *big.Int
}

// NewSigner 创建签名器
func NewSigner(client *ethclient.Client, chainID *big.Int) *Signer {
    return &Signer{
        client:  client,
        chainID: chainID,
    }
}

// SignAndSend 签名并发送交易
func (s *Signer) SignAndSend(ctx context.Context, 
    tx *types.Transaction, 
    privateKey *ecdsa.PrivateKey) (string, error) {
    
    // 创建签名器
    signer := types.LatestSignerForChainID(s.chainID)
    
    // 签名
    signedTx, err := types.SignTx(tx, signer, privateKey)
    if err != nil {
        return "", fmt.Errorf("签名失败: %w", err)
    }
    
    // 发送
    if err := s.client.SendTransaction(ctx, signedTx); err != nil {
        return "", fmt.Errorf("发送交易失败: %w", err)
    }
    
    return signedTx.Hash().Hex(), nil
}

// WaitForReceipt 等待交易确认
func (s *Signer) WaitForReceipt(ctx context.Context, txHash string) (*types.Receipt, error) {
    hash := common.HexToHash(txHash)
    
    for {
        receipt, err := s.client.TransactionReceipt(ctx, hash)
        if err == nil {
            return receipt, nil
        }
        
        select {
        case <-ctx.Done():
            return nil, ctx.Err()
        case <-time.After(2 * time.Second):
            // 继续轮询
        }
    }
}
```

---

### 作业 2：Nonce 管理器

```go
// nonce/manager.go
package nonce

import (
    "context"
    "fmt"
    "sync"
    
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/ethclient"
)

// NonceManager 本地 Nonce 管理器
type NonceManager struct {
    client *ethclient.Client
    mu     sync.Mutex
    nonces map[common.Address]uint64
}

// NewNonceManager 创建 Nonce 管理器
func NewNonceManager(client *ethclient.Client) *NonceManager {
    return &NonceManager{
        client: client,
        nonces: make(map[common.Address]uint64),
    }
}

// GetNonce 获取下一个可用 Nonce（线程安全）
func (m *NonceManager) GetNonce(ctx context.Context, address common.Address) (uint64, error) {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    // 检查本地缓存
    if localNonce, exists := m.nonces[address]; exists {
        m.nonces[address] = localNonce + 1
        return localNonce, nil
    }
    
    // 首次获取，从链上查询
    pendingNonce, err := m.client.PendingNonceAt(ctx, address)
    if err != nil {
        return 0, fmt.Errorf("获取 pending nonce 失败: %w", err)
    }
    
    m.nonces[address] = pendingNonce + 1
    return pendingNonce, nil
}

// ResetNonce 重置 Nonce（交易失败后调用）
func (m *NonceManager) ResetNonce(ctx context.Context, address common.Address) error {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    pendingNonce, err := m.client.PendingNonceAt(ctx, address)
    if err != nil {
        return err
    }
    
    m.nonces[address] = pendingNonce
    return nil
}

// ReleaseNonce 释放 Nonce（交易被拒绝时调用）
func (m *NonceManager) ReleaseNonce(address common.Address, nonce uint64) {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    // 如果释放的 nonce 小于当前值，回退
    if currentNonce, exists := m.nonces[address]; exists && nonce < currentNonce {
        m.nonces[address] = nonce
    }
}
```

---

### 作业 3：Multicall 实现

```go
// multicall/multicall.go
package multicall

import (
    "context"
    "fmt"
    "math/big"
    "strings"
    
    "github.com/ethereum/go-ethereum"
    "github.com/ethereum/go-ethereum/accounts/abi"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/ethclient"
)

// Multicall3 地址（跨链通用）
var Multicall3Address = common.HexToAddress("0xcA11bde05977b3631167028862bE2a173976CA11")

// Call 单个调用
type Call struct {
    Target   common.Address
    CallData []byte
}

// Result 调用结果
type Result struct {
    Success    bool
    ReturnData []byte
}

// Multicall Multicall 客户端
type Multicall struct {
    client *ethclient.Client
    abi    abi.ABI
}

// Multicall3 ABI（简化版）
const multicall3ABI = `[
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate",
        "outputs": [
            {"name": "blockNumber", "type": "uint256"},
            {"name": "returnData", "type": "bytes[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"}
                ],
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]`

// NewMulticall 创建 Multicall 客户端
func NewMulticall(client *ethclient.Client) (*Multicall, error) {
    parsed, err := abi.JSON(strings.NewReader(multicall3ABI))
    if err != nil {
        return nil, err
    }
    
    return &Multicall{
        client: client,
        abi:    parsed,
    }, nil
}

// Aggregate 批量调用（任一失败则全部回滚）
func (m *Multicall) Aggregate(ctx context.Context, calls []Call) ([][]byte, error) {
    // 编码调用数据
    type call struct {
        Target   common.Address
        CallData []byte
    }
    
    encodedCalls := make([]call, len(calls))
    for i, c := range calls {
        encodedCalls[i] = call{
            Target:   c.Target,
            CallData: c.CallData,
        }
    }
    
    data, err := m.abi.Pack("aggregate", encodedCalls)
    if err != nil {
        return nil, fmt.Errorf("编码失败: %w", err)
    }
    
    // 执行调用
    result, err := m.client.CallContract(ctx, ethereum.CallMsg{
        To:   &Multicall3Address,
        Data: data,
    }, nil)
    if err != nil {
        return nil, fmt.Errorf("调用失败: %w", err)
    }
    
    // 解码结果
    var output struct {
        BlockNumber *big.Int
        ReturnData  [][]byte
    }
    
    if err := m.abi.UnpackIntoInterface(&output, "aggregate", result); err != nil {
        return nil, fmt.Errorf("解码失败: %w", err)
    }
    
    return output.ReturnData, nil
}

// Aggregate3 批量调用（允许部分失败）
func (m *Multicall) Aggregate3(ctx context.Context, calls []Call) ([]Result, error) {
    type call3 struct {
        Target       common.Address
        AllowFailure bool
        CallData     []byte
    }
    
    encodedCalls := make([]call3, len(calls))
    for i, c := range calls {
        encodedCalls[i] = call3{
            Target:       c.Target,
            AllowFailure: true,
            CallData:     c.CallData,
        }
    }
    
    data, err := m.abi.Pack("aggregate3", encodedCalls)
    if err != nil {
        return nil, fmt.Errorf("编码失败: %w", err)
    }
    
    result, err := m.client.CallContract(ctx, ethereum.CallMsg{
        To:   &Multicall3Address,
        Data: data,
    }, nil)
    if err != nil {
        return nil, fmt.Errorf("调用失败: %w", err)
    }
    
    // 解码结果
    type resultTuple struct {
        Success    bool
        ReturnData []byte
    }
    var output []resultTuple
    
    if err := m.abi.UnpackIntoInterface(&output, "aggregate3", result); err != nil {
        return nil, fmt.Errorf("解码失败: %w", err)
    }
    
    results := make([]Result, len(output))
    for i, r := range output {
        results[i] = Result{
            Success:    r.Success,
            ReturnData: r.ReturnData,
        }
    }
    
    return results, nil
}
```

---

### 作业 4：Rate Limiter 与 Failover

```go
// rpc/client.go
package rpc

import (
    "context"
    "fmt"
    "sync"
    "time"
    
    "github.com/ethereum/go-ethereum/ethclient"
    "golang.org/x/time/rate"
)

// Config RPC 客户端配置
type Config struct {
    URLs           []string      // 多个 RPC 节点
    RequestsPerSec float64       // 每秒请求数限制
    Timeout        time.Duration // 请求超时
}

// Client 带流控和故障切换的 RPC 客户端
type Client struct {
    clients  []*ethclient.Client
    limiter  *rate.Limiter
    current  int
    mu       sync.RWMutex
    timeout  time.Duration
}

// NewClient 创建 RPC 客户端
func NewClient(cfg Config) (*Client, error) {
    if len(cfg.URLs) == 0 {
        return nil, fmt.Errorf("至少需要一个 RPC URL")
    }
    
    clients := make([]*ethclient.Client, 0, len(cfg.URLs))
    for _, url := range cfg.URLs {
        client, err := ethclient.Dial(url)
        if err != nil {
            // 记录警告但继续
            fmt.Printf("警告: 连接 %s 失败: %v\n", url, err)
            continue
        }
        clients = append(clients, client)
    }
    
    if len(clients) == 0 {
        return nil, fmt.Errorf("无法连接到任何 RPC 节点")
    }
    
    // 创建限流器
    limiter := rate.NewLimiter(rate.Limit(cfg.RequestsPerSec), int(cfg.RequestsPerSec))
    
    return &Client{
        clients: clients,
        limiter: limiter,
        timeout: cfg.Timeout,
    }, nil
}

// getClient 获取当前客户端
func (c *Client) getClient() *ethclient.Client {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.clients[c.current]
}

// failover 切换到下一个节点
func (c *Client) failover() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.current = (c.current + 1) % len(c.clients)
    fmt.Printf("切换到节点 %d\n", c.current)
}

// withRateLimit 执行带限流的操作
func (c *Client) withRateLimit(ctx context.Context, fn func(*ethclient.Client) error) error {
    // 等待令牌
    if err := c.limiter.Wait(ctx); err != nil {
        return fmt.Errorf("限流等待失败: %w", err)
    }
    
    // 设置超时
    ctx, cancel := context.WithTimeout(ctx, c.timeout)
    defer cancel()
    
    // 执行操作，失败时尝试切换节点
    maxRetries := len(c.clients)
    var lastErr error
    
    for i := 0; i < maxRetries; i++ {
        client := c.getClient()
        if err := fn(client); err != nil {
            lastErr = err
            c.failover()
            continue
        }
        return nil
    }
    
    return fmt.Errorf("所有节点都失败: %w", lastErr)
}

// BlockNumber 获取区块号（带限流和故障切换）
func (c *Client) BlockNumber(ctx context.Context) (uint64, error) {
    var result uint64
    err := c.withRateLimit(ctx, func(client *ethclient.Client) error {
        num, err := client.BlockNumber(ctx)
        if err != nil {
            return err
        }
        result = num
        return nil
    })
    return result, err
}

// ... 其他方法类似
```

---

### 作业 5：完整转账示例

```go
// examples/transfer/main.go
package main

import (
    "context"
    "fmt"
    "log"
    "math/big"
    "time"
    
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/core/types"
    "github.com/ethereum/go-ethereum/ethclient"
    
    "eth-client/wallet"
    "eth-client/transaction"
    "eth-client/nonce"
)

func main() {
    // 连接 Anvil
    client, err := ethclient.Dial("http://127.0.0.1:8545")
    if err != nil {
        log.Fatal(err)
    }
    
    chainID, _ := client.ChainID(context.Background())
    
    // 使用 Anvil 预置账户
    // 私钥: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
    fromWallet, err := wallet.NewWalletFromPrivateKey(
        "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    if err != nil {
        log.Fatal(err)
    }
    
    toAddress := common.HexToAddress("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
    
    // 创建组件
    nonceManager := nonce.NewNonceManager(client)
    txBuilder := transaction.NewTxBuilder(client, chainID)
    signer := transaction.NewSigner(client, chainID)
    
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    // 查询转账前余额
    beforeBalance, _ := client.BalanceAt(ctx, toAddress, nil)
    fmt.Printf("接收方转账前余额: %s ETH\n", weiToEth(beforeBalance))
    
    // 构造 EIP-1559 交易
    value := big.NewInt(1e18) // 1 ETH
    tx, err := txBuilder.BuildEIP1559Tx(ctx, fromWallet.Address(), toAddress, value, nil)
    if err != nil {
        log.Fatalf("构造交易失败: %v", err)
    }
    
    // 签名并发送
    txHash, err := signer.SignAndSend(ctx, tx, fromWallet.PrivateKey())
    if err != nil {
        log.Fatalf("发送交易失败: %v", err)
    }
    
    fmt.Printf("交易已发送: %s\n", txHash)
    
    // 等待确认
    receipt, err := signer.WaitForReceipt(ctx, txHash)
    if err != nil {
        log.Fatalf("等待确认失败: %v", err)
    }
    
    if receipt.Status == 1 {
        fmt.Println("✅ 交易成功!")
    } else {
        fmt.Println("❌ 交易失败!")
    }
    
    fmt.Printf("Gas Used: %d\n", receipt.GasUsed)
    
    // 查询转账后余额
    afterBalance, _ := client.BalanceAt(ctx, toAddress, nil)
    fmt.Printf("接收方转账后余额: %s ETH\n", weiToEth(afterBalance))
}

func weiToEth(wei *big.Int) string {
    ethValue := new(big.Float).SetInt(wei)
    ethValue.Quo(ethValue, big.NewFloat(1e18))
    return ethValue.Text('f', 4)
}
```

---

## 📝 知识点总结

### 交易类型对比

| 类型        | Type | 特点                 |
| ----------- | ---- | -------------------- |
| Legacy      | 0    | gasPrice 固定        |
| Access List | 1    | EIP-2930，预热存储槽 |
| Dynamic Fee | 2    | EIP-1559，动态费用   |

### 关键工具函数

| 函数               | 用途                          |
| ------------------ | ----------------------------- |
| `PendingNonceAt`   | 获取包含 pending 交易的 nonce |
| `SuggestGasPrice`  | 建议的 gasPrice               |
| `SuggestGasTipCap` | 建议的 priority fee           |
| `EstimateGas`      | 预估 gas 消耗                 |
| `SendTransaction`  | 广播签名交易                  |

---

## ✅ 今日检查清单

- [ ] 理解并实现了 Legacy 和 EIP-1559 交易构造
- [ ] 实现了线程安全的 Nonce 管理器
- [ ] 完成了 Multicall 批量调用封装
- [ ] 实现了 Rate Limiter 和 Failover 机制
- [ ] 成功在 Anvil 上完成了 ETH 转账

---

## 📌 明日预告

**Day 12: 合约开发 — Foundry 入门**
- Foundry 工具链安装与配置
- forge/cast/anvil 使用详解
- Counter/Bank 合约开发
- Solidity 测试编写
