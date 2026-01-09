# Day 9: LND 开发 (Go)

> **学习时间**：4-6 小时（理论 1.5h + 实战 3-4h + 复习 0.5h）
>
> **核心目标**：掌握 LND 的 gRPC API，使用 Go 开发闪电网络客户端

---

## 🎯 今日学习目标

- [ ] 理解 LND 的架构设计与组件
- [ ] 掌握 Macaroon 鉴权机制
- [ ] 使用 Go 编写 LND gRPC 客户端
- [ ] 实现发票生成与支付监听功能
- [ ] （选修）阅读 LND 源码中的 htlcswitch 包

---

## 📚 理论课：LND 架构详解

### LND 简介

**LND**（Lightning Network Daemon）是最流行的闪电网络实现之一，完全使用 **Go** 语言编写，由 Lightning Labs 维护。

```
┌─────────────────────────────────────────────────────────────────┐
│                      LND 技术栈                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   gRPC API      │  │   REST API      │  │   CLI (lncli)   │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                │
│                     ┌──────────┴──────────┐                     │
│                     │     LND Daemon      │                     │
│                     │     (lnd)           │                     │
│                     └──────────┬──────────┘                     │
│                                │                                │
│  ┌──────────────┬──────────────┼──────────────┬──────────────┐  │
│  │              │              │              │              │  │
│  ▼              ▼              ▼              ▼              ▼  │
│ Wallet       Channel       Router        Invoice        Peer   │
│ Manager      Manager       (寻路)         Manager       Manager │
│                                                                 │
│                     ┌──────────┴──────────┐                     │
│                     │   Bitcoin Backend   │                     │
│                     │ (btcd/bitcoind/    │                     │
│                     │  neutrino)          │                     │
│                     └─────────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### LND 核心组件

| 组件            | 职责         | 关键功能                      |
| --------------- | ------------ | ----------------------------- |
| **Wallet**      | 链上钱包管理 | 地址生成、余额查询、UTXO 管理 |
| **Channel**     | 通道生命周期 | 开/关通道、状态更新           |
| **Router**      | 路由寻路     | 路径计算、费用估算、HTLC 转发 |
| **Invoice**     | 发票管理     | 创建/解码发票、收款确认       |
| **Peer**        | 节点通信     | 连接管理、消息路由            |
| **HTLC Switch** | HTLC 处理    | 接收/转发/结算 HTLC           |

---

### gRPC API 概览

LND 提供丰富的 gRPC API，主要服务包括：

```protobuf
// 主要服务
service Lightning {
    // 节点信息
    rpc GetInfo(GetInfoRequest) returns (GetInfoResponse);
    
    // 钱包操作
    rpc WalletBalance(WalletBalanceRequest) returns (WalletBalanceResponse);
    rpc NewAddress(NewAddressRequest) returns (NewAddressResponse);
    
    // 通道操作
    rpc OpenChannelSync(OpenChannelRequest) returns (ChannelPoint);
    rpc CloseChannel(CloseChannelRequest) returns (stream CloseStatusUpdate);
    rpc ListChannels(ListChannelsRequest) returns (ListChannelsResponse);
    
    // 发票与支付
    rpc AddInvoice(Invoice) returns (AddInvoiceResponse);
    rpc LookupInvoice(PaymentHash) returns (Invoice);
    rpc SendPaymentSync(SendRequest) returns (SendResponse);
    
    // 订阅
    rpc SubscribeInvoices(InvoiceSubscription) returns (stream Invoice);
    rpc SubscribeChannelEvents(ChannelEventSubscription) returns (stream ChannelEventUpdate);
}

// 路由服务
service Router {
    rpc SendPaymentV2(SendPaymentRequest) returns (stream Payment);
    rpc TrackPaymentV2(TrackPaymentRequest) returns (stream Payment);
}

// 钱包服务
service WalletKit {
    rpc ListUnspent(ListUnspentRequest) returns (ListUnspentResponse);
    rpc LeaseOutput(LeaseOutputRequest) returns (LeaseOutputResponse);
}
```

---

### Macaroon 鉴权机制

#### 什么是 Macaroon？

Macaroon 是一种分布式授权凭证，比传统 API Key 更灵活：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Macaroon vs API Key                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  传统 API Key:                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  api_key = "sk_live_xxxxx"                              │    │
│  │  • 全有或全无的权限                                       │    │
│  │  • 无法委托部分权限                                       │    │
│  │  • 需要服务器验证                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Macaroon:                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  macaroon = {                                           │    │
│  │    identifier: "root-key-id",                           │    │
│  │    caveats: [                                           │    │
│  │      "permissions: read,write",                         │    │
│  │      "entity: invoices",                                │    │
│  │      "expires: 2025-01-01"                              │    │
│  │    ],                                                   │    │
│  │    signature: "hmac(...)"                               │    │
│  │  }                                                      │    │
│  │  • 可添加限制条件 (Caveats)                              │    │
│  │  • 可委托派生新的受限 Macaroon                           │    │
│  │  • 客户端可验证                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### LND 的 Macaroon 类型

| 文件                | 权限     | 用途      |
| ------------------- | -------- | --------- |
| `admin.macaroon`    | 完全权限 | 开发/管理 |
| `readonly.macaroon` | 只读权限 | 监控/查询 |
| `invoice.macaroon`  | 发票相关 | 收款服务  |
| `invoices.macaroon` | 发票读写 | 发票管理  |

#### 自定义 Macaroon

```bash
# 创建自定义 Macaroon（只能创建发票，不能支付）
lncli bakemacaroon invoices:read invoices:write --save_to custom.macaroon

# 添加过期时间限制
lncli bakemacaroon --timeout 3600 invoices:write --save_to hourly.macaroon
```

---

## 🛠️ 实战作业

### 作业 1：环境准备

#### 1.1 项目初始化

```bash
mkdir -p ~/blockchain-course/day09-lnd-client
cd ~/blockchain-course/day09-lnd-client
go mod init lnd-client

# 安装依赖
go get github.com/lightningnetwork/lnd/lnrpc
go get google.golang.org/grpc
go get gopkg.in/macaroon.v2
```

#### 1.2 从 Polar 获取连接信息

1. 在 Polar 中启动网络
2. 右键点击 LND 节点 → "Connect"
3. 复制以下信息：
   - gRPC Host (通常是 `127.0.0.1:10001`)
   - TLS Cert 路径
   - Admin Macaroon 路径

---

### 作业 2：LND 客户端封装

#### 2.1 连接配置 (`config/config.go`)

```go
package config

import (
    "encoding/hex"
    "fmt"
    "os"
    "path/filepath"

    "google.golang.org/grpc/credentials"
    "gopkg.in/macaroon.v2"
)

// LNDConfig LND 连接配置
type LNDConfig struct {
    Host         string
    TLSCertPath  string
    MacaroonPath string
}

// NewLNDConfig 从 Polar 目录加载配置
func NewLNDConfig(polarDataDir, nodeName string, grpcPort int) *LNDConfig {
    // Polar 默认路径结构:
    // ~/.polar/networks/1/volumes/lnd/alice/...
    nodeDir := filepath.Join(polarDataDir, "volumes", "lnd", nodeName)
    
    return &LNDConfig{
        Host:         fmt.Sprintf("127.0.0.1:%d", grpcPort),
        TLSCertPath:  filepath.Join(nodeDir, "tls.cert"),
        MacaroonPath: filepath.Join(nodeDir, "data", "chain", "bitcoin", "regtest", "admin.macaroon"),
    }
}

// LoadTLSCredentials 加载 TLS 证书
func (c *LNDConfig) LoadTLSCredentials() (credentials.TransportCredentials, error) {
    return credentials.NewClientTLSFromFile(c.TLSCertPath, "")
}

// LoadMacaroon 加载 Macaroon
func (c *LNDConfig) LoadMacaroon() (string, error) {
    macBytes, err := os.ReadFile(c.MacaroonPath)
    if err != nil {
        return "", fmt.Errorf("读取 macaroon 失败: %w", err)
    }
    
    mac := &macaroon.Macaroon{}
    if err := mac.UnmarshalBinary(macBytes); err != nil {
        return "", fmt.Errorf("解析 macaroon 失败: %w", err)
    }
    
    return hex.EncodeToString(macBytes), nil
}
```

#### 2.2 gRPC 客户端 (`client/lnd_client.go`)

```go
package client

import (
    "context"
    "fmt"
    
    "lnd-client/config"
    
    "github.com/lightningnetwork/lnd/lnrpc"
    "github.com/lightningnetwork/lnd/lnrpc/invoicesrpc"
    "github.com/lightningnetwork/lnd/lnrpc/routerrpc"
    "google.golang.org/grpc"
    "google.golang.org/grpc/metadata"
)

// LNDClient 封装 LND gRPC 客户端
type LNDClient struct {
    conn          *grpc.ClientConn
    lightning     lnrpc.LightningClient
    invoices      invoicesrpc.InvoicesClient
    router        routerrpc.RouterClient
    macaroonHex   string
}

// NewLNDClient 创建 LND 客户端
func NewLNDClient(cfg *config.LNDConfig) (*LNDClient, error) {
    // 加载 TLS 证书
    creds, err := cfg.LoadTLSCredentials()
    if err != nil {
        return nil, fmt.Errorf("加载 TLS 证书失败: %w", err)
    }
    
    // 加载 Macaroon
    macaroonHex, err := cfg.LoadMacaroon()
    if err != nil {
        return nil, fmt.Errorf("加载 Macaroon 失败: %w", err)
    }
    
    // 建立连接
    conn, err := grpc.Dial(
        cfg.Host,
        grpc.WithTransportCredentials(creds),
        grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(50*1024*1024)),
    )
    if err != nil {
        return nil, fmt.Errorf("连接 LND 失败: %w", err)
    }
    
    return &LNDClient{
        conn:        conn,
        lightning:   lnrpc.NewLightningClient(conn),
        invoices:    invoicesrpc.NewInvoicesClient(conn),
        router:      routerrpc.NewRouterClient(conn),
        macaroonHex: macaroonHex,
    }, nil
}

// Close 关闭连接
func (c *LNDClient) Close() error {
    return c.conn.Close()
}

// withMacaroon 添加 Macaroon 到上下文
func (c *LNDClient) withMacaroon(ctx context.Context) context.Context {
    md := metadata.Pairs("macaroon", c.macaroonHex)
    return metadata.NewOutgoingContext(ctx, md)
}

// GetInfo 获取节点信息
func (c *LNDClient) GetInfo(ctx context.Context) (*lnrpc.GetInfoResponse, error) {
    ctx = c.withMacaroon(ctx)
    return c.lightning.GetInfo(ctx, &lnrpc.GetInfoRequest{})
}

// WalletBalance 获取链上钱包余额
func (c *LNDClient) WalletBalance(ctx context.Context) (*lnrpc.WalletBalanceResponse, error) {
    ctx = c.withMacaroon(ctx)
    return c.lightning.WalletBalance(ctx, &lnrpc.WalletBalanceRequest{})
}

// ChannelBalance 获取通道余额
func (c *LNDClient) ChannelBalance(ctx context.Context) (*lnrpc.ChannelBalanceResponse, error) {
    ctx = c.withMacaroon(ctx)
    return c.lightning.ChannelBalance(ctx, &lnrpc.ChannelBalanceRequest{})
}

// ListChannels 列出所有通道
func (c *LNDClient) ListChannels(ctx context.Context) (*lnrpc.ListChannelsResponse, error) {
    ctx = c.withMacaroon(ctx)
    return c.lightning.ListChannels(ctx, &lnrpc.ListChannelsRequest{})
}
```

---

### 作业 3：发票管理

#### 3.1 创建发票

```go
// AddInvoice 创建发票
func (c *LNDClient) AddInvoice(ctx context.Context, amountSats int64, memo string, expirySecs int64) (*lnrpc.AddInvoiceResponse, error) {
    ctx = c.withMacaroon(ctx)
    
    invoice := &lnrpc.Invoice{
        Memo:   memo,
        Value:  amountSats,
        Expiry: expirySecs,
    }
    
    return c.lightning.AddInvoice(ctx, invoice)
}

// AddHoldInvoice 创建 Hold Invoice（可延迟结算）
func (c *LNDClient) AddHoldInvoice(ctx context.Context, hash []byte, amountSats int64, memo string) (*invoicesrpc.AddHoldInvoiceResp, error) {
    ctx = c.withMacaroon(ctx)
    
    return c.invoices.AddHoldInvoice(ctx, &invoicesrpc.AddHoldInvoiceRequest{
        Hash:  hash,
        Memo:  memo,
        Value: amountSats,
    })
}

// LookupInvoice 查询发票
func (c *LNDClient) LookupInvoice(ctx context.Context, paymentHash []byte) (*lnrpc.Invoice, error) {
    ctx = c.withMacaroon(ctx)
    
    return c.lightning.LookupInvoice(ctx, &lnrpc.PaymentHash{
        RHash: paymentHash,
    })
}

// DecodePayReq 解码发票
func (c *LNDClient) DecodePayReq(ctx context.Context, paymentRequest string) (*lnrpc.PayReq, error) {
    ctx = c.withMacaroon(ctx)
    
    return c.lightning.DecodePayReq(ctx, &lnrpc.PayReqString{
        PayReq: paymentRequest,
    })
}
```

#### 3.2 使用示例

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"
    
    "lnd-client/client"
    "lnd-client/config"
)

func main() {
    // 配置（根据你的 Polar 环境调整）
    cfg := &config.LNDConfig{
        Host:         "127.0.0.1:10001",
        TLSCertPath:  "/path/to/tls.cert",
        MacaroonPath: "/path/to/admin.macaroon",
    }
    
    // 创建客户端
    lnd, err := client.NewLNDClient(cfg)
    if err != nil {
        log.Fatalf("创建客户端失败: %v", err)
    }
    defer lnd.Close()
    
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    // 获取节点信息
    info, err := lnd.GetInfo(ctx)
    if err != nil {
        log.Fatalf("获取节点信息失败: %v", err)
    }
    fmt.Printf("节点别名: %s\n", info.Alias)
    fmt.Printf("公钥: %s\n", info.IdentityPubkey)
    fmt.Printf("活跃通道数: %d\n", info.NumActiveChannels)
    
    // 创建发票
    invoice, err := lnd.AddInvoice(ctx, 10000, "测试发票", 3600)
    if err != nil {
        log.Fatalf("创建发票失败: %v", err)
    }
    fmt.Printf("\n发票创建成功!\n")
    fmt.Printf("Payment Request: %s\n", invoice.PaymentRequest)
    fmt.Printf("Payment Hash: %x\n", invoice.RHash)
}
```

---

### 作业 4：支付与订阅

#### 4.1 发送支付

```go
// SendPayment 发送支付（同步）
func (c *LNDClient) SendPayment(ctx context.Context, paymentRequest string, amountSats int64) (*lnrpc.SendResponse, error) {
    ctx = c.withMacaroon(ctx)
    
    return c.lightning.SendPaymentSync(ctx, &lnrpc.SendRequest{
        PaymentRequest: paymentRequest,
        Amt:            amountSats, // 如果发票未指定金额
    })
}

// SendPaymentV2 发送支付（流式，推荐）
func (c *LNDClient) SendPaymentV2(ctx context.Context, paymentRequest string, timeoutSecs int32) (<-chan *lnrpc.Payment, <-chan error) {
    ctx = c.withMacaroon(ctx)
    
    paymentChan := make(chan *lnrpc.Payment)
    errChan := make(chan error, 1)
    
    go func() {
        defer close(paymentChan)
        defer close(errChan)
        
        stream, err := c.router.SendPaymentV2(ctx, &routerrpc.SendPaymentRequest{
            PaymentRequest: paymentRequest,
            TimeoutSeconds: timeoutSecs,
            FeeLimitSat:    1000, // 最大路由费
        })
        if err != nil {
            errChan <- err
            return
        }
        
        for {
            payment, err := stream.Recv()
            if err != nil {
                errChan <- err
                return
            }
            paymentChan <- payment
            
            // 支付完成
            if payment.Status == lnrpc.Payment_SUCCEEDED || 
               payment.Status == lnrpc.Payment_FAILED {
                return
            }
        }
    }()
    
    return paymentChan, errChan
}
```

#### 4.2 订阅发票（收款监听）

```go
// InvoiceSubscriber 发票订阅器
type InvoiceSubscriber struct {
    client *LNDClient
}

// InvoiceUpdate 发票更新事件
type InvoiceUpdate struct {
    PaymentHash   []byte
    PaymentIndex  uint64
    State         lnrpc.Invoice_InvoiceState
    AmountPaid    int64
    SettleDate    int64
    PaymentRequest string
}

// SubscribeInvoices 订阅发票更新
func (c *LNDClient) SubscribeInvoices(ctx context.Context, onUpdate func(*InvoiceUpdate)) error {
    ctx = c.withMacaroon(ctx)
    
    stream, err := c.lightning.SubscribeInvoices(ctx, &lnrpc.InvoiceSubscription{})
    if err != nil {
        return fmt.Errorf("订阅发票失败: %w", err)
    }
    
    for {
        invoice, err := stream.Recv()
        if err != nil {
            return fmt.Errorf("接收发票更新失败: %w", err)
        }
        
        update := &InvoiceUpdate{
            PaymentHash:    invoice.RHash,
            PaymentIndex:   invoice.AddIndex,
            State:          invoice.State,
            AmountPaid:     invoice.AmtPaidSat,
            SettleDate:     invoice.SettleDate,
            PaymentRequest: invoice.PaymentRequest,
        }
        
        onUpdate(update)
    }
}
```

#### 4.3 完整收款服务示例

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "os/signal"
    "syscall"
    
    "lnd-client/client"
    "lnd-client/config"
    
    "github.com/lightningnetwork/lnd/lnrpc"
)

func main() {
    cfg := &config.LNDConfig{
        Host:         "127.0.0.1:10001",
        TLSCertPath:  "/path/to/tls.cert",
        MacaroonPath: "/path/to/admin.macaroon",
    }
    
    lnd, err := client.NewLNDClient(cfg)
    if err != nil {
        log.Fatalf("创建客户端失败: %v", err)
    }
    defer lnd.Close()
    
    // 创建可取消的上下文
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    
    // 处理收款回调
    onInvoicePaid := func(update *client.InvoiceUpdate) {
        switch update.State {
        case lnrpc.Invoice_OPEN:
            fmt.Printf("📝 新发票创建: %x\n", update.PaymentHash[:8])
            
        case lnrpc.Invoice_SETTLED:
            fmt.Printf("✅ 收款成功!\n")
            fmt.Printf("   金额: %d sats\n", update.AmountPaid)
            fmt.Printf("   Hash: %x\n", update.PaymentHash[:8])
            
            // TODO: 在这里触发业务逻辑
            // - 更新订单状态
            // - 通知用户
            // - 释放商品...
            
        case lnrpc.Invoice_CANCELED:
            fmt.Printf("❌ 发票已取消: %x\n", update.PaymentHash[:8])
        }
    }
    
    // 启动订阅
    go func() {
        if err := lnd.SubscribeInvoices(ctx, onInvoicePaid); err != nil {
            log.Printf("订阅中断: %v", err)
        }
    }()
    
    fmt.Println("🚀 收款服务已启动，等待支付...")
    
    // 创建一个测试发票
    invoice, _ := lnd.AddInvoice(ctx, 5000, "商品购买", 3600)
    fmt.Printf("\n请支付此发票:\n%s\n\n", invoice.PaymentRequest)
    
    // 等待退出信号
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
    <-sigChan
    
    fmt.Println("\n正在关闭...")
}
```

---

### 作业 5：通道管理

```go
// OpenChannel 开通道 (同步)
func (c *LNDClient) OpenChannel(ctx context.Context, peerPubkey string, localAmount, pushAmount int64) (*lnrpc.ChannelPoint, error) {
    ctx = c.withMacaroon(ctx)
    
    pubkeyBytes, err := hex.DecodeString(peerPubkey)
    if err != nil {
        return nil, fmt.Errorf("无效的公钥: %w", err)
    }
    
    return c.lightning.OpenChannelSync(ctx, &lnrpc.OpenChannelRequest{
        NodePubkey:         pubkeyBytes,
        LocalFundingAmount: localAmount,
        PushSat:            pushAmount,
    })
}

// CloseChannel 关闭通道
func (c *LNDClient) CloseChannel(ctx context.Context, channelPoint string, force bool) error {
    ctx = c.withMacaroon(ctx)
    
    // 解析 channel point (txid:output_index)
    parts := strings.Split(channelPoint, ":")
    if len(parts) != 2 {
        return fmt.Errorf("无效的 channel point 格式")
    }
    
    txidBytes, err := hex.DecodeString(parts[0])
    if err != nil {
        return err
    }
    
    outputIndex, err := strconv.ParseUint(parts[1], 10, 32)
    if err != nil {
        return err
    }
    
    stream, err := c.lightning.CloseChannel(ctx, &lnrpc.CloseChannelRequest{
        ChannelPoint: &lnrpc.ChannelPoint{
            FundingTxid: &lnrpc.ChannelPoint_FundingTxidBytes{
                FundingTxidBytes: txidBytes,
            },
            OutputIndex: uint32(outputIndex),
        },
        Force: force,
    })
    if err != nil {
        return err
    }
    
    // 等待关闭完成
    for {
        update, err := stream.Recv()
        if err != nil {
            return err
        }
        
        switch u := update.Update.(type) {
        case *lnrpc.CloseStatusUpdate_ChanClose:
            fmt.Printf("通道关闭完成: %x\n", u.ChanClose.ClosingTxid)
            return nil
        case *lnrpc.CloseStatusUpdate_ClosePending:
            fmt.Printf("关闭中... 交易: %x\n", u.ClosePending.Txid)
        }
    }
}
```

---

## 📝 选修：LND 源码阅读

### htlcswitch 包

`htlcswitch` 是 LND 中处理 HTLC 转发的核心包，展示了优秀的 Go 并发编程实践。

```
源码位置: github.com/lightningnetwork/lnd/htlcswitch

关键文件:
├── switch.go        # Switch 主循环，消息路由
├── link.go          # Link 管理单个通道的 HTLC
├── circuit.go       # Circuit 跟踪 HTLC 生命周期
├── payment_result.go # 支付结果处理
└── iterator.go      # 支付尝试迭代器
```

**推荐阅读顺序**：
1. `switch.go` - 理解 Switch 的 goroutine 架构
2. `link.go` - 理解单个通道如何处理 HTLC
3. `circuit.go` - 理解支付路径追踪

**核心设计模式**：

```go
// Switch 消息处理循环 (简化版)
func (s *Switch) htlcForwarder() {
    for {
        select {
        case pkt := <-s.htlcPlex:
            // 根据目标通道转发 HTLC
            s.handlePacket(pkt)
            
        case cmd := <-s.resolutionMsgs:
            // 处理 HTLC 结算
            s.handleResolution(cmd)
            
        case <-s.quit:
            return
        }
    }
}
```

---

## ✅ 今日检查清单

- [ ] 理解了 LND 的架构和核心组件
- [ ] 掌握了 Macaroon 鉴权机制
- [ ] 成功创建并运行了 LND Go 客户端
- [ ] 实现了发票创建和查询功能
- [ ] 实现了支付发送功能
- [ ] 实现了发票订阅（收款监听）

---

## 🔗 参考资源

### 官方文档
- [LND API 文档](https://api.lightning.community/)
- [LND 源码](https://github.com/lightningnetwork/lnd)
- [lnrpc Proto 定义](https://github.com/lightningnetwork/lnd/tree/master/lnrpc)

### 工具
- [Polar](https://lightningpolar.com/) - 可视化测试网络
- [lndconnect](https://github.com/LN-Zap/lndconnect) - 连接字符串生成

---

## 📌 明日预告

**Day 10: 以太坊基础 — Account 模型与 EVM**
- 从 Bitcoin UTXO 到 Ethereum Account 的范式转变
- EVM 架构与 Gas 机制
- MPT 状态存储原理
- go-ethereum 环境配置
