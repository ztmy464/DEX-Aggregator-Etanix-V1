def build_graphql_query(pool1: str, pool2: str, tick_lower: int, tick_upper: int) -> str:
    query = f"""
    query BatchTickQuery {{
      pool1: pool(id: "{pool1}") {{
        tick
        ticks(where: {{
          tickIdx_gte: "{tick_lower}",
          tickIdx_lte: "{tick_upper}"
        }}) {{
          tickIdx
          liquidityNet
        }}
      }}
      pool2: pool(id: "{pool2}") {{
        tick
        ticks(where: {{
          tickIdx_gte: "{tick_lower}",
          tickIdx_lte: "{tick_upper}"
        }}) {{
          tickIdx
          liquidityNet
        }}
      }}
    }}
    """
    return query


pool1 = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
pool2 = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"
tick_lower = 200000
tick_upper = 202000

query_str = build_graphql_query(pool1, pool2, tick_lower, tick_upper)
print(query_str)
