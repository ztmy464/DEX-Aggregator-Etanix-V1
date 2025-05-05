// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../src/interfaces/IERC20.sol";
import {FullMath} from "../../src/uniswap-v3/FullMath.sol";
import {
    UNISWAP_V3_POOL_WBTC_WETH_3000,
    WBTC,
    WETH
} from "../../src/Constants.sol";
// forge test --match-path test/aggregator/UniV3_swap.t.sol --fork-url $FORK_URL -vvv
interface IUniswapV3Pool {
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);

    function slot0()
        external
        view
        returns (
            uint160 sqrtPriceX96,
            int24 tick,
            uint16 observationIndex,
            uint16 observationCardinality,
            uint16 observationCardinalityNext,
            uint8 feeProtocol,
            bool unlocked
        );

    function liquidity() external view returns (uint128);
    
    function token0() external view returns (address);
    function token1() external view returns (address);
}

contract GenericUniswapV3Test is Test {
    // Pool and token instances
    IUniswapV3Pool public pool;
    IERC20 public token0;
    IERC20 public token1;
    
    // Addresses that will be set in setUp()
    address public poolAddress;
    address public token0Address;
    address public token1Address;
    
    // Swap amount (configurable)
    uint256 public swapAmount;
    uint256 public DEAL_TOKEN0_AMOUNT;
    uint256 public DEAL_TOKEN1_AMOUNT;
    uint256 public token1SwapAmount;
    uint256 public token0SwapAmount;
    

    // Constants
    uint256 private constant Q96 = 1 << 96;
    uint160 private constant MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342;
    
    function setUp() public {
        // Default configuration (can be overridden in test functions)
        // Example using WBTC-WETH pool
        poolAddress = address(UNISWAP_V3_POOL_WBTC_WETH_3000); // WBTC-WETH pool
        token0Address = address(WBTC); // WBTC
        token1Address = address(WETH); // WETH
        token1SwapAmount = 1 ether; // 1 for 0 
        token0SwapAmount = 1 ether;
        DEAL_TOKEN0_AMOUNT = 1000000000 ether;
        DEAL_TOKEN1_AMOUNT = 1000000000 ether;
        
        // Initialize contracts
        pool = IUniswapV3Pool(poolAddress);
        token0 = IERC20(token0Address);
        token1 = IERC20(token1Address);
        
        // Verify token addresses match the pool's tokens
        require(pool.token0() == token0Address, "Pool token0 mismatch");
        require(pool.token1() == token1Address, "Pool token1 mismatch");
    }
    
    
    function test_GetPoolInfo() public view {
        // Get slot0 information
        (
            uint160 sqrtPriceX96,
            int24 tick,
            uint16 observationIndex,
            uint16 observationCardinality,
            uint16 observationCardinalityNext,
            uint8 feeProtocol,
            bool unlocked
        ) = pool.slot0();
        
        // Get liquidity information
        uint128 liq = pool.liquidity();
        
        // Log all information
        console.log("Pool Information:");
        console.log("Pool Address:", poolAddress);
        console.log("Token0:", token0Address);
        console.log("Token1:", token1Address);
        console.log("sqrtPriceX96:", sqrtPriceX96);
        console.log("tick:", tick);
        console.log("observationIndex:", observationIndex);
        console.log("observationCardinality:", observationCardinality);
        console.log("observationCardinalityNext:", observationCardinalityNext);
        console.log("feeProtocol:", feeProtocol);
        console.log("unlocked:", unlocked);
        console.log("liquidity:", liq);

        uint256 price = 0;
        price = FullMath.mulDiv(sqrtPriceX96, sqrtPriceX96, Q96) / Q96;
        console2.log("price %e", price);
    }
    
    // Swap token1 for token0 (e.g., WETH for WBTC)
    function test_SwapToken1ForToken0() public {
        deal(token1Address, address(this), DEAL_TOKEN1_AMOUNT);
        
        // Get balance before swap
        uint256 token1BalanceBefore = token1.balanceOf(address(this));
        uint256 token0BalanceBefore = token0.balanceOf(address(this));
        
        // Approve tokens for the pool
        token1.approve(poolAddress, type(uint256).max);
        
        // Create callback contract to handle the swap
        UniswapV3SwapCallback callbackContract = new UniswapV3SwapCallback(
            token1Address, 
            token0Address
        );
        token1.transfer(address(callbackContract), token1SwapAmount);
        
        // Swap parameters
        bool zeroForOne = false; // swapping token1 for token0
        int256 amountSpecified = int256(token1SwapAmount); // positive for exact input
        uint160 sqrtPriceLimitX96 = MAX_SQRT_RATIO - 1; // price limit
        
        console.log("Performing swap of", token1SwapAmount / 1e18, "token1 for token0");
        
        // Execute swap through callback contract
        (int256 amount0, int256 amount1) = callbackContract.executeSwap(
            poolAddress,
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96
        );
        
        // Get balance after swap
        uint256 token1BalanceAfter = token1.balanceOf(address(this));
        uint256 token0BalanceAfter = token0.balanceOf(address(this));
        
        console.log("After swap:");
        assertLt(token1BalanceAfter, token1BalanceBefore);
        assertGt(token0BalanceAfter, token0BalanceBefore);
        
        // Log the swap results
        console.log("amount0 (token0 received):", uint256(-amount0));
        console.log("amount1 (token1 spent):", uint256(amount1));
    }
    
    // Swap token0 for token1 (e.g., WBTC for WETH)
    function test_SwapToken0ForToken1() public {

        deal(token0Address, address(this), DEAL_TOKEN0_AMOUNT);
        
        // Get balance before swap
        uint256 token0BalanceBefore = token0.balanceOf(address(this));
        uint256 token1BalanceBefore = token1.balanceOf(address(this));
        
        // Approve tokens for the pool
        token0.approve(poolAddress, type(uint256).max);
        
        // Create callback contract to handle the swap
        UniswapV3SwapCallback callbackContract = new UniswapV3SwapCallback(
            token1Address, 
            token0Address
        );
        token0.transfer(address(callbackContract), token0SwapAmount);
        
        // Swap parameters
        bool zeroForOne = true; // swapping token0 for token1
        int256 amountSpecified = int256(token0SwapAmount); // positive for exact input
        uint160 sqrtPriceLimitX96 = 4295128739 + 1; // MIN_SQRT_RATIO + 1
        
        console.log("Performing swap of token0 for token1");
        
        // Execute swap through callback contract
        (int256 amount0, int256 amount1) = callbackContract.executeSwap(
            poolAddress,
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96
        );
        
        // Get balance after swap
        uint256 token0BalanceAfter = token0.balanceOf(address(this));
        uint256 token1BalanceAfter = token1.balanceOf(address(this));
        
        console.log("After swap:");
        assertLt(token0BalanceAfter, token0BalanceBefore);
        assertGt(token1BalanceAfter, token1BalanceBefore);
        
        // Log the swap results
        console.log("amount0 (token0 spent):", uint256(amount0));
        console.log("amount1 (token1 received):", uint256(-amount1));
    }

}
// Helper contract to handle Uniswap V3 callbacks
contract UniswapV3SwapCallback {
    IERC20 public immutable token0;
    IERC20 public immutable token1;
    
    constructor(address _token1, address _token0) {
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }
    
    // Function to execute the swap
    function executeSwap(
        address poolAddress,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external returns (int256 amount0, int256 amount1) { 
        (amount0, amount1) = IUniswapV3Pool(poolAddress).swap(
            address(this),
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96, 
            abi.encode(msg.sender)
        );
        // If amount0 is negative, it means this contract received token0 from the pool
        if (amount0 < 0) {
            // Transfer the received token0 back to the user who initiated the swap
            token0.transfer(msg.sender, uint256(-amount0));
        }
        if (amount1 < 0) {
           token1.transfer(msg.sender, uint256(-amount1));
        }

       return (amount0, amount1);
    }
    
    // Callback function that Uniswap V3 will call during the swap
    function uniswapV3SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        // Decode the callback data to get the caller
        address caller = abi.decode(data, (address));
        
        // If amount0 is positive, we need to pay token0 to the pool
        if (amount0Delta > 0) {
            token0.transfer(msg.sender, uint256(amount0Delta));
        }
        
        // If amount1 is positive, we need to pay token1 to the pool
        if (amount1Delta > 0) {
            token1.transfer(msg.sender, uint256(amount1Delta));
        }
    }
}