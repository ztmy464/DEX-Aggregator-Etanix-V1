// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";

import {
    UNISWAP_V2_PAIR_USDC_WETH,
    WBTC,
    WETH
} from "../../src/Constants.sol";
// forge test --match-path test/aggregator/UniV2_swap.t.sol --fork-url $FORK_URL -vvv

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function swap(uint amount0Out, uint amount1Out, address to, bytes calldata data) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
    function price0CumulativeLast() external view returns (uint);
    function price1CumulativeLast() external view returns (uint);
}

interface IUniswapV2Factory {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
}

contract GenericUniswapV2Test is Test {
    // Pool and token instances
    IUniswapV2Pair public pair;
    IERC20 public token0;
    IERC20 public token1;
    
    // Addresses that will be set in setUp()
    address public pairAddress;
    address public token0Address;
    address public token1Address;
    
    // Swap amount (configurable)
    uint256 public DEAL_TOKEN0_AMOUNT;
    uint256 public DEAL_TOKEN1_AMOUNT;
    uint256 public token1SwapAmount;
    uint256 public token0SwapAmount;
    
    function setUp() public {
        // Default configuration (can be overridden in test functions)
        // Example using WBTC-WETH pair
        pairAddress = address(UNISWAP_V2_PAIR_USDC_WETH); // WBTC-WETH pair
        token0SwapAmount = 1 ether;
        token1SwapAmount = 1 ether;
        DEAL_TOKEN0_AMOUNT = 1000000000 ether;
        DEAL_TOKEN1_AMOUNT = 1000000000 ether;
        
        // Initialize contracts
        pair = IUniswapV2Pair(pairAddress);
        token0Address = pair.token0();
        token1Address = pair.token1();
        token0 = IERC20(token0Address);
        token1 = IERC20(token1Address);
        
    }
    
    function test_GetPairInfo() public view {
        // Get reserves information
        (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast) = pair.getReserves();
        
        // Log all information
        console.log("Pair Information:");
        console.log("Pair Address:", pairAddress);
        console.log("Token0:", token0Address);
        console.log("Token1:", token1Address);
        console.log("Reserve0:", reserve0);
        console.log("Reserve1:", reserve1);
        console.log("Block Timestamp Last:", blockTimestampLast);
        
        // Calculate price
        uint256 price0 = 0;
        uint256 price1 = 0;
        if (reserve0 > 0 && reserve1 > 0) {
            // Price of token1 in terms of token0
            price0 = (uint256(reserve1) * 1e18) / uint256(reserve0);
            // Price of token0 in terms of token1
            price1 = (uint256(reserve0) * 1e18) / uint256(reserve1);
        }
        console.log("Price0 (token1/token0):", price0);
        console.log("Price1 (token0/token1):", price1);
    }
    
    // Swap token1 for token0 (e.g., WETH for WBTC)
    function test_SwapToken1ForToken0() public {
        deal(token1Address, address(this), DEAL_TOKEN1_AMOUNT);
        
        // Get balance before swap
        uint256 token1BalanceBefore = token1.balanceOf(address(this));
        uint256 token0BalanceBefore = token0.balanceOf(address(this));
        
        // Get reserves to calculate expected output
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        
        // Calculate amount out using UniswapV2 formula: amount_out = (amount_in * reserve_out * 997) / (reserve_in * 1000 + amount_in * 997)
        uint256 amountIn = token1SwapAmount;
        uint256 amountOut = (amountIn * uint256(reserve0) * 997) / (uint256(reserve1) * 1000 + amountIn * 997);
        
        console.log("Performing swap of", amountIn / 1e18, "token1 for token0");
        console.log("Expected token0 output:", amountOut);
        
        // Transfer tokens to the pair
        token1.transfer(pairAddress, amountIn);
        
        // Execute swap
        pair.swap(amountOut, 0, address(this), new bytes(0));
        
        // Get balance after swap
        uint256 token1BalanceAfter = token1.balanceOf(address(this));
        uint256 token0BalanceAfter = token0.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("token1 spent:", token1BalanceBefore - token1BalanceAfter);
        console.log("token0 received:", token0BalanceAfter - token0BalanceBefore);
        
        assertEq(token1BalanceBefore - token1BalanceAfter, amountIn);
        assertEq(token0BalanceAfter - token0BalanceBefore, amountOut);
    }
    
    // Swap token0 for token1 (e.g., WBTC for WETH)
    function test_SwapToken0ForToken1() public {
        deal(token0Address, address(this), DEAL_TOKEN0_AMOUNT);
        
        // Get balance before swap
        uint256 token0BalanceBefore = token0.balanceOf(address(this));
        uint256 token1BalanceBefore = token1.balanceOf(address(this));
        
        // Get reserves to calculate expected output
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        
        // Calculate amount out using UniswapV2 formula: amount_out = (amount_in * reserve_out * 997) / (reserve_in * 1000 + amount_in * 997)
        uint256 amountIn = token0SwapAmount;
        uint256 amountOut = (amountIn * uint256(reserve1) * 997) / (uint256(reserve0) * 1000 + amountIn * 997);
        
        console.log("Performing swap of token0 for token1");
        console.log("Expected token1 output:", amountOut);
        
        // Transfer tokens to the pair
        token0.transfer(pairAddress, amountIn);
        
        // Execute swap
        pair.swap(0, amountOut, address(this), new bytes(0));
        
        // Get balance after swap
        uint256 token0BalanceAfter = token0.balanceOf(address(this));
        uint256 token1BalanceAfter = token1.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("token0 spent:", token0BalanceBefore - token0BalanceAfter);
        console.log("token1 received:", token1BalanceAfter - token1BalanceBefore);
        
        assertEq(token0BalanceBefore - token0BalanceAfter, amountIn);
        assertEq(token1BalanceAfter - token1BalanceBefore, amountOut);
    }
    
    // Bonus function to test exact output swap (token0 for token1)
    function test_SwapToken0ForExactToken1() public {
        deal(token0Address, address(this), DEAL_TOKEN0_AMOUNT);
        
        // Get balance before swap
        uint256 token0BalanceBefore = token0.balanceOf(address(this));
        uint256 token1BalanceBefore = token1.balanceOf(address(this));
        
        // Get reserves to calculate required input
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        
        // Fixed amount of token1 we want to receive
        uint256 amountOut = 1 ether;

        // amount_in = (reserve_in * amount_out * 1000) / ((reserve_out - amount_out) * 997)
        uint256 amountIn = (uint256(reserve0) * amountOut * 1000) / ((uint256(reserve1) - amountOut) * 997) + 1;
        
        console.log("Performing swap for exact token1 output");
        console.log("Required token0 input:", amountIn);
        console.log("Expected token1 output:", amountOut);
        
        // Transfer tokens to the pair
        token0.transfer(pairAddress, amountIn);
        
        // Execute swap
        pair.swap(0, amountOut, address(this), new bytes(0));
        
        // Get balance after swap
        uint256 token0BalanceAfter = token0.balanceOf(address(this));
        uint256 token1BalanceAfter = token1.balanceOf(address(this));
        
        console.log("After swap:");
        console.log("token0 spent:", token0BalanceBefore - token0BalanceAfter);
        console.log("token1 received:", token1BalanceAfter - token1BalanceBefore);
        
        assertEq(token0BalanceBefore - token0BalanceAfter, amountIn);
        assertEq(token1BalanceAfter - token1BalanceBefore, amountOut);
    }
}