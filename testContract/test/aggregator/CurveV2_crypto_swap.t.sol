// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.19;

import "forge-std/Test.sol";

interface IMath {
    function get_y(
        uint256 ANN,
        uint256 gamma,
        uint256[3] memory x,
        uint256 D,
        uint256 i
    ) external view returns (uint256[2] memory);
}

interface IPool {
    function exchange(
        uint256 i,
        uint256 j,
        uint256 dx,
        uint256 min_dy
    ) external payable returns (uint256);
    function balances(uint256 index) external view returns (uint256);
    function price_scale(uint256 k) external view returns (uint256);
    function precisions() external view returns (uint256[3] memory);
    function D() external view returns (uint256);
}

contract MathTest is Test {
    address constant MATH_ADDRESS = 0xcBFf3004a20dBfE2731543AA38599A526e0fD6eE;
    address constant POOL_ADDRESS = 0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B;
    uint256 PRECISION = 1e18;
    IMath math;
    IPool pool;
    uint256[3] precisions;
    uint256[2] priceScales;
    uint256[3] balances;
    uint256 D;
    uint256[3] xp;
    function setUp() public {
        math = IMath(MATH_ADDRESS);
        pool = IPool(POOL_ADDRESS);
        precisions = pool.precisions();
        D = pool.D();

        for (uint256 i = 0; i < 2; i++) {
            priceScales[i] = pool.price_scale(i);
        }
        for (uint256 i = 0; i < 3; i++) {
            balances[i] = pool.balances(i);
        }
        console.log("price_scale: [%s, %s]", priceScales[0], priceScales[1]);

        console.log("balances: [%s, %s, %s]", balances[0], balances[1], balances[2]);

    }

    function testNewtonY() public {

        uint256 ANN = 1707629;
        uint256 gamma = 11809167828997;

        uint256 i = 0;
        uint256 j = 1;

        for (uint256 i = 0; i < 3; i++) {
            xp[i] = balances[i];
        }

        xp[i] = xp[i] + 10000*1e6;
        xp[0] = xp[0] * precisions[0];
        xp[1] = xp[1] * priceScales[0] * precisions[1] / PRECISION;
        xp[2] = xp[2] * priceScales[1] * precisions[2] / PRECISION;

        console.log("xp: [%s, %s, %s]", xp[0], xp[1], xp[2]);

        uint256[2] memory result = math.get_y(ANN, gamma, xp, D, j);
        emit log_named_uint("Result0", result[0]);
        emit log_named_uint("Result1", result[1]);

        uint256 dy = xp[j] - result[0];
        if (j > 0) {
            dy = dy * PRECISION / priceScales[j - 1];
        }
        // dy /= precisions[j];
        emit log_named_uint("dy", dy);
    }

    function testExchange() public {
        uint256 i = 0;
        uint256 j = 1;
        uint256 dx = 1000000;
        uint256 min_dy = 0; 

        uint256 received = pool.exchange(
            i,
            j,
            dx,
            min_dy
        );
        console.log("Exchange received dy =", received);
    }
}
