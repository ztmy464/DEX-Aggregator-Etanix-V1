// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";
import {
    BALANCER_STABLE_POOL_OSETH_WETH,
    OSETH,
    WETH
} from "../../src/Constants.sol";
// forge test --match-path test/aggregator/Balancer_ECLP_swap.t.sol --fork-url $FORK_URL -vvv

// Balancer StablePool interface with onSwap function
interface IBalancerStablePool {
    struct SwapRequest {
        uint256 lastChangeBlock;
        address from;
        address to;
        bytes userData;
    }

    function onSwap(
        SwapRequest calldata swapRequest,
        uint256[] calldata balances,
        uint256 indexIn,
        uint256 indexOut
    ) external returns (uint256);
    
    function getPoolId() external view returns (bytes32);
    function getVault() external view returns (address);
    function getTokens() external view returns (address[] memory);
}

// Balancer Vault interface
interface IBalancerVault {
    enum SwapKind { GIVEN_IN, GIVEN_OUT }
    
    struct SingleSwap {
        bytes32 poolId;
        SwapKind kind;
        address assetIn;
        address assetOut;
        uint256 amount;
        bytes userData;
    }
    
    struct FundManagement {
        address sender;
        bool fromInternalBalance;
        address payable recipient;
        bool toInternalBalance;
    }
    
    function swap(
        SingleSwap memory singleSwap,
        FundManagement memory funds,
        uint256 limit,
        uint256 deadline
    ) external payable returns (uint256);

    function getPoolTokens(bytes32 poolId) external view returns (
        address[] memory tokens,
        uint256[] memory balances,
        uint256 lastChangeBlock
    );
}

contract BalancerStableSwapTest is Test {
    // Pool and token instances
    IBalancerStablePool public pool;
    IBalancerVault public vault;
    IERC20 public osETH;
    IERC20 public wETH;
    
    // Addresses that will be set in setUp()
    address public poolAddress;
    address public osETHAddress;
    address public wETHAddress;
    address public vaultAddress;
    bytes32 public poolId;
    
    // Token indices in pool
    uint256 public osETHIndex;
    uint256 public wETHIndex;
    
    // Swap amounts (configurable)
    uint256 public DEAL_OSETH_AMOUNT;
    uint256 public DEAL_WETH_AMOUNT;
    uint256 public osETHSwapAmount;
    uint256 public wETHSwapAmount;
    
    function setUp() public {
        // Default configuration
        poolAddress = address(BALANCER_STABLE_POOL_OSETH_WETH);
        osETHAddress = address(OSETH);
        wETHAddress = address(WETH);
        
        // Initialize swap amounts (both tokens have similar value as they're pegged to ETH)
        osETHSwapAmount = 1 ether;
        wETHSwapAmount = 1 ether;
        DEAL_OSETH_AMOUNT = 1000 ether;
        DEAL_WETH_AMOUNT = 1000 ether;
        
        // Initialize contracts
        pool = IBalancerStablePool(poolAddress);
        poolId = pool.getPoolId();
        vaultAddress = pool.getVault();
        vault = IBalancerVault(vaultAddress);
        osETH = IERC20(osETHAddress);
        wETH = IERC20(wETHAddress);
        
        // Determine token indices in the pool
        (address[] memory tokens, , ) = vault.getPoolTokens(poolId);
        bool foundOsETH = false;
        bool foundWETH = false;
        
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == osETHAddress) {
                osETHIndex = i;
                foundOsETH = true;
            }
            if (tokens[i] == wETHAddress) {
                wETHIndex = i;
                foundWETH = true;
            }
        }
        
        require(foundOsETH, "Pool does not contain osETH");
        require(foundWETH, "Pool does not contain wETH");
    }
    
    // Swap osETH for wETH
    function test_SwapToken0ForToken1() public {
        deal(osETHAddress, address(this), DEAL_OSETH_AMOUNT);
        
        // Get balance before swap
        uint256 osETHBalanceBefore = osETH.balanceOf(address(this));
        uint256 wETHBalanceBefore = wETH.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        osETH.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        console.log("Pool Information:");
        console.log("osETH index:", osETHIndex);
        console.log("wETH index:", wETHIndex);
        console.log("Pool osETH balance:", balances[osETHIndex]);
        console.log("Pool wETH balance:", balances[wETHIndex]);
        console.log("Performing swap of osETH for wETH");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: osETHAddress,
            assetOut: wETHAddress,
            amount: osETHSwapAmount,
            userData: ""
        });
        
        IBalancerVault.FundManagement memory funds = IBalancerVault.FundManagement({
            sender: address(this),
            fromInternalBalance: false,
            recipient: payable(address(this)),
            toInternalBalance: false
        });
        
        // Execute swap through vault
        uint256 amountOut = vault.swap(
            singleSwap,
            funds,
            0,
            block.timestamp + 600 // Deadline: 10 minutes
        );
        
        // Get balance after swap
        uint256 osETHBalanceAfter = osETH.balanceOf(address(this));
        uint256 wETHBalanceAfter = wETH.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("osETH spent:", osETHBalanceBefore - osETHBalanceAfter);
        console.log("wETH received:", wETHBalanceAfter - wETHBalanceBefore);
        
        assertEq(osETHBalanceBefore - osETHBalanceAfter, osETHSwapAmount);
        assertEq(wETHBalanceAfter - wETHBalanceBefore, amountOut);
    }
    
    // Swap wETH for osETH
    function test_SwapToken1ForToken0() public {
        deal(wETHAddress, address(this), DEAL_WETH_AMOUNT);
        
        // Get balance before swap
        uint256 wETHBalanceBefore = wETH.balanceOf(address(this));
        uint256 osETHBalanceBefore = osETH.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        wETH.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        console.log("Pool Information:");
        console.log("osETH index:", osETHIndex);
        console.log("wETH index:", wETHIndex);
        console.log("Pool osETH balance:", balances[osETHIndex]);
        console.log("Pool wETH balance:", balances[wETHIndex]);
        console.log("Performing swap of wETH for osETH");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: wETHAddress,
            assetOut: osETHAddress,
            amount: wETHSwapAmount,
            userData: ""
        });
        
        IBalancerVault.FundManagement memory funds = IBalancerVault.FundManagement({
            sender: address(this),
            fromInternalBalance: false,
            recipient: payable(address(this)),
            toInternalBalance: false
        });
        
        // Execute swap through vault
        uint256 amountOut = vault.swap(
            singleSwap,
            funds,
            0,
            block.timestamp + 600 // Deadline: 10 minutes
        );
        
        // Get balance after swap
        uint256 wETHBalanceAfter = wETH.balanceOf(address(this));
        uint256 osETHBalanceAfter = osETH.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("wETH spent:", wETHBalanceBefore - wETHBalanceAfter);
        console.log("osETH received:", osETHBalanceAfter - osETHBalanceBefore);
        
        assertEq(wETHBalanceBefore - wETHBalanceAfter, wETHSwapAmount);
        assertEq(osETHBalanceAfter - osETHBalanceBefore, amountOut);
    }
    
    // Additional test for exact output swaps (optional)
    function test_SwapExactOut() public {
        deal(osETHAddress, address(this), DEAL_OSETH_AMOUNT);
        
        // Get balance before swap
        uint256 osETHBalanceBefore = osETH.balanceOf(address(this));
        uint256 wETHBalanceBefore = wETH.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        osETH.approve(vaultAddress, type(uint256).max);
        
        // Fixed amount of wETH we want to receive
        uint256 exactWETHOut = 1 ether;
        
        // Create swap parameters for exact output
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_OUT, // Exact output
            assetIn: osETHAddress,
            assetOut: wETHAddress,
            amount: exactWETHOut,
            userData: ""
        });
        
        IBalancerVault.FundManagement memory funds = IBalancerVault.FundManagement({
            sender: address(this),
            fromInternalBalance: false,
            recipient: payable(address(this)),
            toInternalBalance: false
        });
        
        console.log("Performing exact output swap for", exactWETHOut, "wETH");
        
        // Execute swap through vault
        uint256 amountIn = vault.swap(
            singleSwap,
            funds,
            type(uint256).max, // Maximum input (in production, set a reasonable limit)
            block.timestamp + 600 // Deadline: 10 minutes
        );
        
        // Get balance after swap
        uint256 osETHBalanceAfter = osETH.balanceOf(address(this));
        uint256 wETHBalanceAfter = wETH.balanceOf(address(this));
        
        console.log("After exact output swap:");
        console.log("osETH spent:", osETHBalanceBefore - osETHBalanceAfter);
        console.log("wETH received:", wETHBalanceAfter - wETHBalanceBefore);
        
        assertEq(osETHBalanceBefore - osETHBalanceAfter, amountIn);
        assertEq(wETHBalanceAfter - wETHBalanceBefore, exactWETHOut);
    }
}