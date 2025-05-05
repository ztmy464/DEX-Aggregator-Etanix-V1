// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";
import {
    BALANCER_GYRO_POOL_GYD_SDAI,
    GYD,
    SDAI
} from "../../src/Constants.sol";
// forge test --match-path test/aggregator/Balancer_ECLP_swap.t.sol --fork-url $FORK_URL -vvv

// ECLP Pool interface with onSwap function
interface IECLPPool {
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

// Balancer Vault interface (same interface is used for ECLP)
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

contract ECLPSwapTest is Test {
    // Pool and token instances
    IECLPPool public pool;
    IBalancerVault public vault;
    IERC20 public gyd;
    IERC20 public sdai;
    
    // Addresses that will be set in setUp()
    address public poolAddress;
    address public gydAddress;
    address public sdaiAddress;
    address public vaultAddress;
    bytes32 public poolId;
    
    // Swap amounts (configurable)
    uint256 public DEAL_GYD_AMOUNT;
    uint256 public DEAL_SDAI_AMOUNT;
    uint256 public gydSwapAmount;
    uint256 public sdaiSwapAmount;
    
    function setUp() public {
        // Default configuration - Using the constants from your import
        poolAddress = address(BALANCER_GYRO_POOL_GYD_SDAI);
        gydAddress = address(GYD);
        sdaiAddress = address(SDAI);
        
        // Initialize swap amounts (both are stablecoins, so using similar amounts)
        gydSwapAmount = 1000 ether; // 1000 GYD
        sdaiSwapAmount = 1000 ether; // 1000 sDAI
        DEAL_GYD_AMOUNT = 100000 ether; // 100K GYD for testing
        DEAL_SDAI_AMOUNT = 100000 ether; // 100K sDAI for testing
        
        // Initialize contracts
        pool = IECLPPool(poolAddress);
        poolId = pool.getPoolId();
        vaultAddress = pool.getVault();
        vault = IBalancerVault(vaultAddress);
        gyd = IERC20(gydAddress);
        sdai = IERC20(sdaiAddress);
        
        // Verify pool tokens
        (address[] memory tokens, , ) = vault.getPoolTokens(poolId);
        bool hasGYD = false;
        bool hasSDai = false;
        
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == gydAddress) hasGYD = true;
            if (tokens[i] == sdaiAddress) hasSDai = true;
        }
        
        require(hasGYD, "Pool does not contain GYD");
        require(hasSDai, "Pool does not contain sDAI");
    }
    
    // Swap GYD for sDAI
    function test_SwapGYDForSDAI() public {
        deal(gydAddress, address(this), DEAL_GYD_AMOUNT);
        
        // Get balance before swap
        uint256 gydBalanceBefore = gyd.balanceOf(address(this));
        uint256 sdaiBalanceBefore = sdai.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        gyd.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        // Find token indexes
        uint256 gydBalance = 0;
        uint256 sdaiBalance = 0;
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == gydAddress) gydBalance = balances[i];
            if (tokens[i] == sdaiAddress) sdaiBalance = balances[i];
        }
        
        console.log("Pool GYD balance:", gydBalance);
        console.log("Pool sDAI balance:", sdaiBalance);
        console.log("Performing swap of GYD for sDAI");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: gydAddress,
            assetOut: sdaiAddress,
            amount: gydSwapAmount,
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
        uint256 gydBalanceAfter = gyd.balanceOf(address(this));
        uint256 sdaiBalanceAfter = sdai.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("GYD spent:", gydBalanceBefore - gydBalanceAfter);
        console.log("sDAI received:", sdaiBalanceAfter - sdaiBalanceBefore);
        
        assertEq(gydBalanceBefore - gydBalanceAfter, gydSwapAmount);
        assertEq(sdaiBalanceAfter - sdaiBalanceBefore, amountOut);
    }
    
    // Swap sDAI for GYD
    function test_SwapSDAIForGYD() public {
        deal(sdaiAddress, address(this), DEAL_SDAI_AMOUNT);
        
        // Get balance before swap
        uint256 sdaiBalanceBefore = sdai.balanceOf(address(this));
        uint256 gydBalanceBefore = gyd.balanceOf(address(this));
        
        // Approve tokens to be used by the vault
        sdai.approve(vaultAddress, type(uint256).max);
        
        // Get current pool state for reference
        (address[] memory tokens, uint256[] memory balances, uint256 lastChangeBlock) = vault.getPoolTokens(poolId);
        
        // Find token indexes
        uint256 gydBalance = 0;
        uint256 sdaiBalance = 0;
        for (uint i = 0; i < tokens.length; i++) {
            if (tokens[i] == gydAddress) gydBalance = balances[i];
            if (tokens[i] == sdaiAddress) sdaiBalance = balances[i];
        }
        
        console.log("Pool GYD balance:", gydBalance);
        console.log("Pool sDAI balance:", sdaiBalance);
        console.log("Performing swap of sDAI for GYD");
        
        // Create swap parameters
        IBalancerVault.SingleSwap memory singleSwap = IBalancerVault.SingleSwap({
            poolId: poolId,
            kind: IBalancerVault.SwapKind.GIVEN_IN,
            assetIn: sdaiAddress,
            assetOut: gydAddress,
            amount: sdaiSwapAmount,
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
        uint256 sdaiBalanceAfter = sdai.balanceOf(address(this));
        uint256 gydBalanceAfter = gyd.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("sDAI spent:", sdaiBalanceBefore - sdaiBalanceAfter);
        console.log("GYD received:", gydBalanceAfter - gydBalanceBefore);
        
        assertEq(sdaiBalanceBefore - sdaiBalanceAfter, sdaiSwapAmount);
        assertEq(gydBalanceAfter - gydBalanceBefore, amountOut);
    }
}