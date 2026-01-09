# Day 13: Solidity 基础语法与 ERC-20

> **学习时间**：4-6 小时（理论 2h + 实战 3h + 复习 0.5h）
>
> **核心目标**：掌握 Solidity 核心语法，实现 ERC-20 代币合约

---

## 🎯 今日学习目标

- [ ] 掌握 Solidity 数据类型与变量
- [ ] 理解函数可见性与修饰器
- [ ] 理解事件（Events）的使用
- [ ] 实现完整的 ERC-20 代币合约
- [ ] 使用 Fuzz 测试验证合约安全性

---

## 📚 理论课：Solidity 核心语法

### 数据类型

#### 值类型

```solidity
// 布尔
bool public isActive = true;

// 整数（有符号/无符号）
uint256 public totalSupply;    // 0 到 2^256-1
int256 public temperature;      // -2^255 到 2^255-1
uint8 public decimals = 18;     // 0 到 255

// 地址
address public owner;                    // 20 字节
address payable public recipient;        // 可接收 ETH

// 定长字节
bytes32 public hash;
bytes4 public selector;

// 枚举
enum Status { Pending, Active, Completed }
Status public status = Status.Pending;
```

#### 引用类型

```solidity
// 动态数组
uint256[] public numbers;

// 定长数组
uint256[10] public fixedNumbers;

// 映射
mapping(address => uint256) public balances;
mapping(address => mapping(address => uint256)) public allowances;

// 结构体
struct User {
    string name;
    uint256 balance;
    bool isActive;
}
mapping(address => User) public users;

// 字符串和动态字节
string public name = "My Token";
bytes public data;
```

---

### 变量存储位置

```
┌────────────────────────────────────────────────────────────────┐
│                    Solidity 存储位置                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  storage  ─── 持久化存储（链上）                                 │
│               • 状态变量默认存储位置                             │
│               • Gas 成本高                                     │
│               • 修改需要交易                                   │
│                                                                │
│  memory   ─── 临时存储（函数执行期间）                          │
│               • 函数参数、局部变量                              │
│               • 函数返回后销毁                                 │
│               • Gas 成本低                                     │
│                                                                │
│  calldata ─── 只读存储（外部调用数据）                          │
│               • external 函数参数                              │
│               • 不可修改                                       │
│               • Gas 成本最低                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

```solidity
contract StorageExample {
    // storage: 状态变量
    uint256[] public numbers;
    
    // memory: 函数内临时数据
    function processArray(uint256[] memory input) public pure returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < input.length; i++) {
            sum += input[i];
        }
        return sum;
    }
    
    // calldata: 外部调用的只读数据（更省 Gas）
    function processExternal(uint256[] calldata input) external pure returns (uint256) {
        uint256 sum = 0;
        for (uint256 i = 0; i < input.length; i++) {
            sum += input[i];
        }
        return sum;
    }
}
```

---

### 函数可见性

```solidity
contract VisibilityExample {
    // public: 内部和外部都可调用，自动生成 getter
    function publicFunc() public pure returns (string memory) {
        return "public";
    }
    
    // external: 只能从外部调用（不能内部调用）
    function externalFunc() external pure returns (string memory) {
        return "external";
    }
    
    // internal: 只能内部调用或被继承合约调用
    function internalFunc() internal pure returns (string memory) {
        return "internal";
    }
    
    // private: 只能在当前合约内调用
    function privateFunc() private pure returns (string memory) {
        return "private";
    }
    
    // 调用示例
    function callFunctions() public view returns (string memory) {
        publicFunc();      // ✓
        // externalFunc(); // ✗ 不能内部调用
        internalFunc();    // ✓
        privateFunc();     // ✓
        
        this.externalFunc(); // ✓ 通过 this 可以调用 external
        return "done";
    }
}
```

---

### 函数修饰器

```solidity
// view: 只读取状态，不修改
function getBalance() public view returns (uint256) {
    return balances[msg.sender];
}

// pure: 不读取也不修改状态
function add(uint256 a, uint256 b) public pure returns (uint256) {
    return a + b;
}

// payable: 可接收 ETH
function deposit() public payable {
    balances[msg.sender] += msg.value;
}

// 无修饰器: 可读写状态
function transfer(address to, uint256 amount) public {
    balances[msg.sender] -= amount;
    balances[to] += amount;
}
```

---

### 自定义修饰器（Modifier）

```solidity
contract ModifierExample {
    address public owner;
    bool public paused;
    
    constructor() {
        owner = msg.sender;
    }
    
    // 权限检查修饰器
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _; // 继续执行被修饰的函数
    }
    
    // 暂停检查修饰器
    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }
    
    // 参数验证修饰器
    modifier validAddress(address addr) {
        require(addr != address(0), "Invalid address");
        _;
    }
    
    // 使用多个修饰器
    function transfer(address to, uint256 amount) 
        public 
        whenNotPaused 
        validAddress(to) 
    {
        // 函数逻辑
    }
    
    // 只有 owner 可以暂停
    function pause() public onlyOwner {
        paused = true;
    }
}
```

---

### 事件（Events）

```solidity
contract EventExample {
    // 定义事件
    event Transfer(
        address indexed from,    // indexed: 可被过滤
        address indexed to,
        uint256 value            // 非 indexed: 存储在 data 中
    );
    
    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );
    
    // 触发事件
    function transfer(address to, uint256 amount) public {
        // ... 转账逻辑
        emit Transfer(msg.sender, to, amount);
    }
}
```

**indexed 的作用**：
- 最多 3 个 indexed 参数
- indexed 参数存储在 topic 中，可被高效过滤
- 非 indexed 参数存储在 data 中

---

## 🛠️ 实战：ERC-20 代币合约

### IERC-20 接口

```solidity
// src/interfaces/IERC20.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    // 事件
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    // 读取函数
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    
    // 写入函数
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}
```

### ERC-20 实现

```solidity
// src/MyToken.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IERC20.sol";

/// @title MyToken - 一个简单的 ERC-20 代币
/// @notice 实现 ERC-20 标准的所有功能
contract MyToken is IERC20 {
    // ============ 状态变量 ============
    
    string private _name;
    string private _symbol;
    uint8 private constant _decimals = 18;
    uint256 private _totalSupply;
    
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // ============ 构造函数 ============
    
    constructor(string memory name_, string memory symbol_, uint256 initialSupply) {
        _name = name_;
        _symbol = symbol_;
        _mint(msg.sender, initialSupply * 10 ** _decimals);
    }
    
    // ============ 只读函数 ============
    
    function name() public view override returns (string memory) {
        return _name;
    }
    
    function symbol() public view override returns (string memory) {
        return _symbol;
    }
    
    function decimals() public pure override returns (uint8) {
        return _decimals;
    }
    
    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }
    
    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    // ============ 写入函数 ============
    
    function transfer(address to, uint256 amount) public override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) public override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        _spendAllowance(from, msg.sender, amount);
        _transfer(from, to, amount);
        return true;
    }
    
    // ============ 扩展函数（非标准） ============
    
    /// @notice 增加授权额度
    function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
        _approve(msg.sender, spender, _allowances[msg.sender][spender] + addedValue);
        return true;
    }
    
    /// @notice 减少授权额度
    function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
        uint256 currentAllowance = _allowances[msg.sender][spender];
        require(currentAllowance >= subtractedValue, "ERC20: decreased allowance below zero");
        _approve(msg.sender, spender, currentAllowance - subtractedValue);
        return true;
    }
    
    // ============ 内部函数 ============
    
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "ERC20: transfer from the zero address");
        require(to != address(0), "ERC20: transfer to the zero address");
        
        uint256 fromBalance = _balances[from];
        require(fromBalance >= amount, "ERC20: transfer amount exceeds balance");
        
        unchecked {
            _balances[from] = fromBalance - amount;
            _balances[to] += amount;
        }
        
        emit Transfer(from, to, amount);
    }
    
    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "ERC20: mint to the zero address");
        
        _totalSupply += amount;
        unchecked {
            _balances[account] += amount;
        }
        
        emit Transfer(address(0), account, amount);
    }
    
    function _burn(address account, uint256 amount) internal {
        require(account != address(0), "ERC20: burn from the zero address");
        
        uint256 accountBalance = _balances[account];
        require(accountBalance >= amount, "ERC20: burn amount exceeds balance");
        
        unchecked {
            _balances[account] = accountBalance - amount;
            _totalSupply -= amount;
        }
        
        emit Transfer(account, address(0), amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    function _spendAllowance(address owner, address spender, uint256 amount) internal {
        uint256 currentAllowance = _allowances[owner][spender];
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, "ERC20: insufficient allowance");
            unchecked {
                _approve(owner, spender, currentAllowance - amount);
            }
        }
    }
}
```

### ERC-20 测试

```solidity
// test/MyToken.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {MyToken} from "../src/MyToken.sol";

contract MyTokenTest is Test {
    MyToken public token;
    
    address public owner = makeAddr("owner");
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    
    uint256 public constant INITIAL_SUPPLY = 1_000_000;
    
    function setUp() public {
        vm.prank(owner);
        token = new MyToken("MyToken", "MTK", INITIAL_SUPPLY);
    }
    
    // ============ 元数据测试 ============
    
    function test_Name() public view {
        assertEq(token.name(), "MyToken");
    }
    
    function test_Symbol() public view {
        assertEq(token.symbol(), "MTK");
    }
    
    function test_Decimals() public view {
        assertEq(token.decimals(), 18);
    }
    
    function test_TotalSupply() public view {
        assertEq(token.totalSupply(), INITIAL_SUPPLY * 1e18);
    }
    
    function test_OwnerBalance() public view {
        assertEq(token.balanceOf(owner), INITIAL_SUPPLY * 1e18);
    }
    
    // ============ Transfer 测试 ============
    
    function test_Transfer() public {
        uint256 amount = 1000 * 1e18;
        
        vm.prank(owner);
        bool success = token.transfer(alice, amount);
        
        assertTrue(success);
        assertEq(token.balanceOf(alice), amount);
        assertEq(token.balanceOf(owner), (INITIAL_SUPPLY * 1e18) - amount);
    }
    
    function test_TransferEmitsEvent() public {
        uint256 amount = 1000 * 1e18;
        
        vm.expectEmit(true, true, false, true);
        emit MyToken.Transfer(owner, alice, amount);
        
        vm.prank(owner);
        token.transfer(alice, amount);
    }
    
    function test_RevertWhen_TransferExceedsBalance() public {
        uint256 amount = (INITIAL_SUPPLY + 1) * 1e18;
        
        vm.prank(owner);
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        token.transfer(alice, amount);
    }
    
    function test_RevertWhen_TransferToZeroAddress() public {
        vm.prank(owner);
        vm.expectRevert("ERC20: transfer to the zero address");
        token.transfer(address(0), 1000);
    }
    
    // ============ Approve 测试 ============
    
    function test_Approve() public {
        uint256 amount = 1000 * 1e18;
        
        vm.prank(owner);
        bool success = token.approve(alice, amount);
        
        assertTrue(success);
        assertEq(token.allowance(owner, alice), amount);
    }
    
    function test_ApproveEmitsEvent() public {
        uint256 amount = 1000 * 1e18;
        
        vm.expectEmit(true, true, false, true);
        emit MyToken.Approval(owner, alice, amount);
        
        vm.prank(owner);
        token.approve(alice, amount);
    }
    
    // ============ TransferFrom 测试 ============
    
    function test_TransferFrom() public {
        uint256 approveAmount = 1000 * 1e18;
        uint256 transferAmount = 500 * 1e18;
        
        // Owner 授权给 Alice
        vm.prank(owner);
        token.approve(alice, approveAmount);
        
        // Alice 代 Owner 转账给 Bob
        vm.prank(alice);
        token.transferFrom(owner, bob, transferAmount);
        
        assertEq(token.balanceOf(bob), transferAmount);
        assertEq(token.allowance(owner, alice), approveAmount - transferAmount);
    }
    
    function test_RevertWhen_TransferFromInsufficientAllowance() public {
        vm.prank(owner);
        token.approve(alice, 100 * 1e18);
        
        vm.prank(alice);
        vm.expectRevert("ERC20: insufficient allowance");
        token.transferFrom(owner, bob, 200 * 1e18);
    }
    
    // ============ 额度调整测试 ============
    
    function test_IncreaseAllowance() public {
        vm.startPrank(owner);
        token.approve(alice, 1000 * 1e18);
        token.increaseAllowance(alice, 500 * 1e18);
        vm.stopPrank();
        
        assertEq(token.allowance(owner, alice), 1500 * 1e18);
    }
    
    function test_DecreaseAllowance() public {
        vm.startPrank(owner);
        token.approve(alice, 1000 * 1e18);
        token.decreaseAllowance(alice, 300 * 1e18);
        vm.stopPrank();
        
        assertEq(token.allowance(owner, alice), 700 * 1e18);
    }
    
    // ============ Fuzz 测试 ============
    
    function testFuzz_Transfer(address to, uint256 amount) public {
        vm.assume(to != address(0));
        vm.assume(to != owner);
        amount = bound(amount, 1, INITIAL_SUPPLY * 1e18);
        
        vm.prank(owner);
        token.transfer(to, amount);
        
        assertEq(token.balanceOf(to), amount);
    }
    
    function testFuzz_Approve(address spender, uint256 amount) public {
        vm.assume(spender != address(0));
        
        vm.prank(owner);
        token.approve(spender, amount);
        
        assertEq(token.allowance(owner, spender), amount);
    }
    
    function testFuzz_TransferFrom(uint256 approveAmount, uint256 transferAmount) public {
        approveAmount = bound(approveAmount, 1, INITIAL_SUPPLY * 1e18);
        transferAmount = bound(transferAmount, 1, approveAmount);
        
        vm.prank(owner);
        token.approve(alice, approveAmount);
        
        vm.prank(alice);
        token.transferFrom(owner, bob, transferAmount);
        
        assertEq(token.balanceOf(bob), transferAmount);
        assertEq(token.allowance(owner, alice), approveAmount - transferAmount);
    }
    
    // ============ 极限值测试 ============
    
    function test_TransferMaxSupply() public {
        uint256 maxSupply = INITIAL_SUPPLY * 1e18;
        
        vm.prank(owner);
        token.transfer(alice, maxSupply);
        
        assertEq(token.balanceOf(alice), maxSupply);
        assertEq(token.balanceOf(owner), 0);
    }
    
    function test_ApproveMaxUint() public {
        vm.prank(owner);
        token.approve(alice, type(uint256).max);
        
        assertEq(token.allowance(owner, alice), type(uint256).max);
        
        // 无限授权不会减少
        vm.prank(alice);
        token.transferFrom(owner, bob, 1000 * 1e18);
        
        assertEq(token.allowance(owner, alice), type(uint256).max);
    }
}
```

---

### 运行测试

```bash
# 运行所有测试
forge test

# 显示 Gas 报告
forge test --gas-report

# 运行 Fuzz 测试更多轮次
forge test --fuzz-runs 500

# 覆盖率报告
forge coverage
```

---

## 📝 知识点总结

### ERC-20 核心函数

| 函数                             | 说明     |
| -------------------------------- | -------- |
| `totalSupply()`                  | 总供应量 |
| `balanceOf(address)`             | 查询余额 |
| `transfer(to, amount)`           | 直接转账 |
| `approve(spender, amount)`       | 授权额度 |
| `allowance(owner, spender)`      | 查询授权 |
| `transferFrom(from, to, amount)` | 代理转账 |

### 安全考虑

| 问题         | 解决方案                     |
| ------------ | ---------------------------- |
| 零地址检查   | require(addr != address(0))  |
| 余额检查     | require(balance >= amount)   |
| 授权额度检查 | require(allowance >= amount) |
| 整数溢出     | Solidity 0.8+ 自动检查       |

---

## ✅ 今日检查清单

- [ ] 掌握了 Solidity 基本数据类型
- [ ] 理解了函数可见性和修饰器
- [ ] 实现了完整的 ERC-20 合约
- [ ] 编写了全面的测试用例
- [ ] 运行了 Fuzz 测试验证安全性

---

## 📌 明日预告

**Day 14: Week 2 整合与 Mini Project**
- Week 2 知识点复习
- 完整 ERC-20 Mini Project
- 部署到 Sepolia 测试网
- Etherscan 合约验证
