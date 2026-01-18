# Day 21: Mini Project 完成与部署

> **学习时间**：4-5 小时（开发 3h + 测试 1h + 部署 1h）
>
> **核心目标**：完成 **Portfolio Tracker** 的核心功能开发、E2E 测试与 Docker 部署。

---

## 🎯 今日目标

- [ ] 实现 Transfer 事件的 ABI 解析
- [ ] 完成 API 服务（余额查询、历史记录）
- [ ] 编写 E2E 集成测试
- [ ] 使用 Docker Compose 部署完整服务
- [ ] Week 3 知识总结

---

## 🛠️ 实战任务

### Part 1: 完成事件解析

更新 `cmd/indexer/main.go` 中的日志处理：

```go
// 在 main.go 中添加解析逻辑
import (
    "database/sql"
    "math/big"
    "portfolio/token"
    "github.com/ethereum/go-ethereum/accounts/abi"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/core/types"
    "strings"
)

// ERC-20 Transfer(address,address,uint256) 事件签名的 Keccak256 哈希
var transferSig = common.HexToHash("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")

func processLogs(db *sql.DB, logs []types.Log) error {
    tokenABI, _ := abi.JSON(strings.NewReader(token.MyTokenMetaData.ABI))
    
    tx, _ := db.Begin()
    defer tx.Rollback()
    
    for _, vLog := range logs {
        if vLog.Topics[0] != transferSig {
            continue
        }
        
        // 解析 indexed 参数
        from := common.HexToAddress(vLog.Topics[1].Hex())
        to := common.HexToAddress(vLog.Topics[2].Hex())
        
        // 解析 data 中的 amount
        var event struct{ Value *big.Int }
        tokenABI.UnpackIntoInterface(&event, "Transfer", vLog.Data)
        
        // 插入数据库
        _, err := tx.Exec(`
            INSERT INTO transfers (tx_hash, log_index, block_number, block_hash, from_address, to_address, amount)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (tx_hash, log_index) DO NOTHING
        `, vLog.TxHash.Hex(), vLog.Index, vLog.BlockNumber, vLog.BlockHash.Hex(),
           from.Hex(), to.Hex(), event.Value.String())
        
        if err != nil {
            return err
        }
    }
    
    return tx.Commit()
}
```

### Part 2: API 服务

创建 `cmd/api/main.go`:

```go
package main

import (
    "database/sql"
    "net/http"
    "os"

    "github.com/gin-gonic/gin"
    _ "github.com/lib/pq"
)

func main() {
    db, _ := sql.Open("postgres", os.Getenv("DB_DSN"))
    defer db.Close()

    r := gin.Default()

    // 查询余额
    r.GET("/api/balance/:address", func(c *gin.Context) {
        address := c.Param("address")

        var balance string
        err := db.QueryRow(`
            SELECT 
                COALESCE((SELECT SUM(amount) FROM transfers WHERE to_address = $1), 0) -
                COALESCE((SELECT SUM(amount) FROM transfers WHERE from_address = $1), 0)
        `, address).Scan(&balance)

        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }

        c.JSON(http.StatusOK, gin.H{"address": address, "balance": balance})
    })

    // 查询历史
    r.GET("/api/history/:address", func(c *gin.Context) {
        address := c.Param("address")
        rows, _ := db.Query(`
            SELECT tx_hash, block_number, from_address, to_address, amount
            FROM transfers
            WHERE from_address = $1 OR to_address = $1
            ORDER BY block_number DESC LIMIT 50
        `, address)
        defer rows.Close()

        var history []map[string]interface{}
        for rows.Next() {
            var tx, from, to, amount string
            var block int64
            rows.Scan(&tx, &block, &from, &to, &amount)
            history = append(history, map[string]interface{}{
                "tx": tx, "block": block, "from": from, "to": to, "amount": amount,
            })
        }

        c.JSON(http.StatusOK, history)
    })

    r.Run(":8080")
}
```

### Part 3: E2E 测试

创建 `test/e2e_test.go`:

```go
package test

import (
    "context"
    "math/big"
    "testing"
    "time"

    "github.com/ethereum/go-ethereum/accounts/abi/bind"
    "github.com/ethereum/go-ethereum/common"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/ethclient"

    "portfolio/token"
)

func TestTokenTransferFlow(t *testing.T) {
    client, _ := ethclient.Dial("http://127.0.0.1:8545")
    
    deployerKey, _ := crypto.HexToECDSA("ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    auth, _ := bind.NewKeyedTransactorWithChainID(deployerKey, big.NewInt(31337))

    // 1. 部署
    addr, _, inst, _ := token.DeployMyToken(auth, client, big.NewInt(1e18))
    t.Logf("Token deployed: %s", addr.Hex())

    // 2. 转账
    user := common.HexToAddress("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
    tx, _ := inst.Transfer(auth, user, big.NewInt(1000))
    bind.WaitMined(context.Background(), client, tx)

    // 3. 等待 Indexer
    time.Sleep(5 * time.Second)

    // 4. 验证 API (省略 HTTP 调用)
    t.Log("E2E Test Passed!")
}
```

### Part 4: Docker 部署

创建 `docker-compose.yml`:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: portfolio
    ports:
      - "5432:5432"
    volumes:
      - ./migrations:/docker-entrypoint-initdb.d

  indexer:
    build:
      context: .
      dockerfile: Dockerfile
      target: indexer
    environment:
      RPC_URL: ${RPC_URL}
      DB_DSN: postgres://admin:secret@postgres:5432/portfolio?sslmode=disable
      TOKEN_ADDRESS: ${TOKEN_ADDRESS}
    depends_on:
      - postgres

  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: api
    ports:
      - "8080:8080"
    environment:
      DB_DSN: postgres://admin:secret@postgres:5432/portfolio?sslmode=disable
    depends_on:
      - postgres
```

创建 `Dockerfile`:

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o /indexer ./cmd/indexer
RUN go build -o /api ./cmd/api

FROM alpine:3.18 AS indexer
COPY --from=builder /indexer /indexer
CMD ["/indexer"]

FROM alpine:3.18 AS api
COPY --from=builder /api /api
CMD ["/api"]
```

---

## ✅ 提交检查清单

### 功能完整性
- [ ] Indexer 正确解析并存储 Transfer 事件
- [ ] API `/api/balance/:address` 返回正确余额
- [ ] API `/api/history/:address` 返回交易历史
- [ ] E2E 测试通过

### 部署验收
- [ ] `docker compose up` 一键启动
- [ ] 服务间网络正确连接
- [ ] Indexer 日志显示正常同步

---

## 🎓 Week 3 总结

恭喜完成 Week 3！你现在掌握了：

| 技能              | 内容                                 |
| :---------------- | :----------------------------------- |
| **Solidity 进阶** | ABI 编码、Storage Layout、Proxy 模式 |
| **Go 合约交互**   | `abigen` 绑定、部署、读写、事件监听  |
| **测试工程化**    | Go Test + Anvil 实现自动化 E2E       |
| **后端服务**      | Custom Indexer、Reorg 处理、API 服务 |
| **容器化**        | Docker Compose 多服务编排            |

---

## 📌 Week 4 预告

**Week 4: 资产与 DeFi 基础**
- Day 22: ERC-721 (NFT) 与 ERC-1155
- Day 23-24: AMM 与 Uniswap V2/V3 原理
- Day 25-26: 闪电贷与套利
- Day 27-28: Mini Project - DEX 聚合器
