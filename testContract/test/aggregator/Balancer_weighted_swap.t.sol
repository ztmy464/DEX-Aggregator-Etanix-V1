// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";
import {
    BALANCER_POOL_20WSTETH_80AAVE,
    WSTETH,
    AAVE
} from "../../src/Constants.sol";
// forge test --match-path test/aggregator/Balancer_weighted_swap.t.sol --fork-url $FORK_URL -vvv

// Balancer Pool interface with onSwap function
interface IBalancerPool {
    struct SwapRequest {
        uint256 lastChangeBlock;
        address from;
        address to;
        bytes userData;
    }

    function onSwap(
        SwapRequest calldata request,
        uint256 balanceTokenIn,
        uint256 balanceTokenOut
    ) external returns (uint256);
    
    function getPoolId() external view returns (bytes32);
    function getVault() external view returns (address);
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

contract BalancerSwapTest is Test {
    // Pool and token instances
    IBalancerPool public pool;
    IBalancerVault public vault;
    IERC20 public wstETH;
    IERC20 public aave;
    
    // Addresses that will be set in setUp()
    address public poolAddress;
    address public wstETHAddress;
    address public aaveAddress;
    address public vaultAddress;
    bytes32 public poolId;
    
    // Swap amounts (configurable)
    uint256 public DEAL_WSTETH_AMOUNT;
    uint256 public DEAL_AAVE_AMOUNT;
    uint256 public wstETHSwapAmount;
    uint256 public aaveSwapAmount;
    
    function setUp() public {
        // Default configuration
        poolAddress = address(BALANCER_POOL_20WSTETH_80AAVE);
        wstETHAddress = address(WSTETH);
        aaveAddress = address(AAVE);
        
        // Initialize swap amounts
        wstETHSwapAmount = 1 ether;
        aaveSwapAmount = 10 ether; // AAVE usually has lower value than wstETH
        DEAL_WSTETH_AMOUNT = 1000 ether;
        DEAL_AAVE_AMOUNT = 10000 ether;
        
        // Initialize contracts
        pool = IBalancerPool(poolAddress);
        poolId = pool.getPoolId();
        vaultAddress = pool.getVault();
        vault = IBalancerVault(vaultAddress);
        wstETH = IERC20(wstETHAddress);
        aave = IERC20(aaveAddress);
        
        // Verify pool tokens
        (address[] memory tokens, , ) = vault.getPoolTokens(poolId);
        bool hasWstETH = false;
        bool hasAAVE = false;
        
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == wstETHAddress) hasWstETH = true;
            if (tokens[i] == aaveAddress) hasAAVE = true;
        }
        
        require(hasWstETH, "Pool does not contain wstETH");
        require(hasAAVE, "Pool does not contain AAVE");
    }
    
    // Swap wstETH for AAVE (20% token for 80% token)
    function test_SwapToken0ForToken1() public {
        deal(wstETHAddress, address(this), DEAL_WSTETH_AMOUNT);
        
        // Get balance before swap
        uint256 wstETHBalanceBefore = wstETH.balanceOf(address(this));
        uint256 aaveBalanceBefore = aave.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        wstETH.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        // Find token indexes
        uint256 wstETHBalance = 0;
        uint256 aaveBalance = 0;
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == wstETHAddress) wstETHBalance = balances[i];
            if (tokens[i] == aaveAddress) aaveBalance = balances[i];
        }
        
        console.log("Pool wstETH balance:", wstETHBalance);
        console.log("Pool AAVE balance:", aaveBalance);
        console.log("Performing swap of wstETH for AAVE");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: wstETHAddress,
            assetOut: aaveAddress,
            amount: wstETHSwapAmount,
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
            0, // No minimum output (in production code, always set a minimum)
            block.timestamp + 600 // Deadline: 10 minutes
        );
        
        // Get balance after swap
        uint256 wstETHBalanceAfter = wstETH.balanceOf(address(this));
        uint256 aaveBalanceAfter = aave.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("wstETH spent:", wstETHBalanceBefore - wstETHBalanceAfter);
        console.log("AAVE received:", aaveBalanceAfter - aaveBalanceBefore);
        
        assertEq(wstETHBalanceBefore - wstETHBalanceAfter, wstETHSwapAmount);
        assertEq(aaveBalanceAfter - aaveBalanceBefore, amountOut);
    }
    
    // Swap AAVE for wstETH (80% token for 20% token)
    function test_SwapToken1ForToken0() public {
        deal(aaveAddress, address(this), DEAL_AAVE_AMOUNT);
        
        // Get balance before swap
        uint256 aaveBalanceBefore = aave.balanceOf(address(this));
        uint256 wstETHBalanceBefore = wstETH.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        aave.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        // Find token indexes
        uint256 wstETHBalance = 0;
        uint256 aaveBalance = 0;
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == wstETHAddress) wstETHBalance = balances[i];
            if (tokens[i] == aaveAddress) aaveBalance = balances[i];
        }
        
        console.log("Pool wstETH balance:", wstETHBalance);
        console.log("Pool AAVE balance:", aaveBalance);
        console.log("Performing swap of AAVE for wstETH");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: aaveAddress,
            assetOut: wstETHAddress,
            amount: aaveSwapAmount,
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
            0, // No minimum output (in production code, always set a minimum)
            block.timestamp + 600 // Deadline: 10 minutes
        );
        
        // Get balance after swap
        uint256 aaveBalanceAfter = aave.balanceOf(address(this));
        uint256 wstETHBalanceAfter = wstETH.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("AAVE spent:", aaveBalanceBefore - aaveBalanceAfter);
        console.log("wstETH received:", wstETHBalanceAfter - wstETHBalanceBefore);
        
        assertEq(aaveBalanceBefore - aaveBalanceAfter, aaveSwapAmount);
        assertEq(wstETHBalanceAfter - wstETHBalanceBefore, amountOut);
    }
    
}