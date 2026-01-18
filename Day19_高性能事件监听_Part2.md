# Day 19: 高性能事件监听与 Custom Indexer (Part 2)

> **学习时间**：4-6 小时（理论 1.5h + 实战 4h + 复习 0.5h）
>
> **核心目标**：完成 Indexer 的核心功能实现 —— 使用 ABI 解析 Log 数据，并将整个服务容器化部署。

---

## 🎯 今日学习目标

- [ ] 掌握 `abigen` 的 Event Binding 用法
- [ ] 实现 Log Data 的手动解析（不使用 abigen 的场景）
- [ ] 掌握数据库批量写入（Batch Insert）优化技巧
- [ ] 使用 Docker Compose 编排 Postgres + Indexer App
- [ ] 实现简单的 GraphQL/REST API 供前端查询

---

## 📚 理论课：ABI 解析与部署架构

### 1. 解析 Log 的两种方式

当从 `FilterLogs` 拿到 `types.Log` 后，我们需要将其 data (Hex) 转换为 Go 结构体。

| 方式                 | 适用场景           | 优点             | 缺点                            |
| :------------------- | :----------------- | :--------------- | :------------------------------ |
| **Abigen Binding**   | 合约源码已知且固定 | 类型安全，开发快 | 每次合约修改需重新生成代码      |
| **ABI JSON Parsing** | 合约未知或动态加载 | 灵活性高         | 只有 `interface{}` 类型，需断言 |

### 2. Docker 化部署

生产环境的 Indexer 通常是长期运行的后台服务。

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: indexer_db
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  indexer:
    build: .
    restart: always
    environment:
      RPC_URL: "https://eth-mainnet.g.alchemy.com/v2/..."
      DB_DSN: "postgres://postgres:secret@db:5432/indexer_db"
    depends_on:
      - db
```

---

## 🛠️ 实战作业

### 作业 1: 使用 Abigen 解析 Log

在 Day 16 我们生成了 `store.go`，它包含 `contract.UnpackLog` 方法。但在 Indexer 中，我们通常处理的是原始 `types.Log`。

```go
// parser.go
package main

import (
	"day16/store" // 引用之前的生成包
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"strings"
)

// ParseStoreItemSet 解析 Transfer 事件
func ParseStoreItemSet(vLog types.Log, storeABI abi.ABI) (*store.StoreItemSet, error) {
    var event store.StoreItemSet
    
    // 1. 验证 Topic[0] (Event Signature Hash)
    // 实际项目中应与 contractABI.Events["ItemSet"].ID 比较
    
    // 2. 解包 Data (非 indexed 字段)
    // 注意：UnpackIntoInterface 只能解包 Data 部分，无法解包 Topics
    err := storeABI.UnpackIntoInterface(&event, "ItemSet", vLog.Data)
    if err != nil {
        return nil, err
    }
    
    // 3. 手动解析 Topics (indexed 字段)
    // Topic[0] 是签名, Topic[1] 是 Key
    event.Key = common.BytesToHash(vLog.Topics[1].Bytes()) // 假设 Key 是 indexed bytes32
    
    // 补充系统字段
    event.Raw = vLog
    
    return &event, nil
}
```

### 作业 2: 不使用 Binding 的通用解析

如果只给了一个 ABI JSON 字符串，怎么解析？

```go
// dynamic_parser.go
package main

import (
    "github.com/ethereum/go-ethereum/accounts/abi"
    "github.com/ethereum/go-ethereum/core/types"
    "strings"
)

func ParseDynamic(abiJSON string, vLog types.Log) (map[string]interface{}, error) {
    parsedABI, err := abi.JSON(strings.NewReader(abiJSON))
    if err != nil {
        return nil, err
    }
    
    // 根据 Topic[0] 找到对应 Event
    event, err := parsedABI.EventByID(vLog.Topics[0])
    if err != nil {
        return nil, err
    }
    
    result := make(map[string]interface{})
    
    // 解析 Data
    if len(vLog.Data) > 0 {
        err = parsedABI.UnpackIntoMap(result, event.Name, vLog.Data)
        if err != nil {
            return nil, err
        }
    }
    
    // 解析 Indexed 参数 (Topics)
    // ⚠️ 注意：go-ethereum 没有直接暴露 abi.ParseTopics 公开函数
    // 以下是简化的教学演示，实际项目推荐使用 abigen 生成的 binding
    // 或手动遍历 event.Inputs 解析 Topics：
    // indexedCount := 0
    // for _, arg := range event.Inputs {
    //     if arg.Indexed {
    //         result[arg.Name] = vLog.Topics[1+indexedCount]
    //         indexedCount++
    //     }
    // }
    
    return result, nil
}
```

### 作业 3: 构建 API 服务 (Gin)

使用 Gin 框架提供查询接口。

```go
// api.go
package main

import (
    "database/sql"
    "github.com/gin-gonic/gin"
    "net/http"
)

func StartAPIServer(db *sql.DB) {
    r := gin.Default()
    
    r.GET("/api/events", func(c *gin.Context) {
        // 支持分页
        limit := c.DefaultQuery("limit", "10")
        offset := c.DefaultQuery("offset", "0")
        
        rows, err := db.Query("SELECT tx_hash, block_number, from_addr, to_addr, amount FROM transfers ORDER BY block_number DESC LIMIT $1 OFFSET $2", limit, offset)
        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        defer rows.Close()
        
        var results []map[string]interface{}
        for rows.Next() {
            var r TransferRecord
            rows.Scan(&r.TxHash, &r.BlockNumber, &r.From, &r.To, &r.Amount)
            results = append(results, r.ToMap())
        }
        
        c.JSON(http.StatusOK, gin.H{"data": results})
    })
    
    r.Run(":8080")
}
```

### 作业 4: 性能优化——批量插入

不要每处理一条 Log 就 Insert 一次数据库。

```go
// batch_writer.go
package main

import (
    "database/sql"
    "fmt"
    "sync"
    "time"
)

const BatchSize = 1000
const FlushInterval = 5 * time.Second

type BatchProcessor struct {
    buffer []LogModel
    db     *sql.DB
    mu     sync.Mutex
}

func (p *BatchProcessor) Add(log LogModel) {
    p.mu.Lock()
    defer p.mu.Unlock()
    
    p.buffer = append(p.buffer, log)
    
    if len(p.buffer) >= BatchSize {
        p.Flush()
    }
}

func (p *BatchProcessor) Flush() {
    if len(p.buffer) == 0 {
        return
    }
    
    // 使用 pgx (Postgres Driver) 的 CopyFrom 实现极速写入
    // 或者构造 INSERT INTO ... VALUES (...), (...), (...)
    
    fmt.Printf("批量写入 %d 条记录\n", len(p.buffer))
    p.buffer = nil
}

// 还需要一个 Ticker 定时 Flush，防止数据滞留
```

---

## 📝 知识点总结

### 1. Indexed vs Non-Indexed 解析
- **Non-Indexed**: 存储在 `log.Data` 区域，ABI 编码，容易解析 (`Unpack`).
- **Indexed**: 存储在 `log.Topics` 列表，是 32 字节的哈希值（对于复杂类型）。
- **陷阱**: `string` 和 `bytes` 等动态类型如果设为 `indexed`，Topic 中存的是 `keccak256(value)`，**无法还原原始内容**。

### 2. 数据库写入性能
- **单条 Insert**: ~1000 TPS
- **批量 Insert**: ~50,000 TPS
- Indexer 是典型的写密集型应用，批量写入是必须的。

### 3. 系统完整性
- 必须确保 `Indexer` 挂掉重启后，能够从 DB 的 `last_block` 无缝继续。这就是为什么我们在 Day 18 强调 `cursor` 表的重要性。

---

## ✅ 今日检查清单

- [ ] 能够解析包含 `indexed` 参数的复杂 Event
- [ ] 编写了 Dockerfile 和 docker-compose.yml
- [ ] 实现了 API 接口供前端查询历史数据
- [ ] 实现了 1000 条/批次的批量写入逻辑

---

## 📌 明日预告

**Day 20-21: Week 3 整合与 Mini Project**
- 实战项目：构建一个链上资产看板 (Portfolio Tracker)
- 集成：前端 (React) + API (Go Indexer) + 合约 (Foundry E2E)
