# Branch 1: 基线严格角色 (Baseline Strict Character) — 详细实验报告

**实验描述**: 最小约束，进化限制极紧 (price_bias±0.05, quantity_bias±2, forecast_bias±1)，保留原始性格
**总轮数**: 16
**模型**: qwen-plus (阿里云百炼)

## 一、核心指标总览

| Agent | 累计利润 | 平均轮利润 | 利润波动 | 最大回撤 | 胜率 | 最终声誉 | 平均定价 | 总进货量 | 平均服务率 | 倾销次数 | 违约次数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | $+430.68 | $+26.92 | 91.18 | 114.65 | 62.5% | 0.749 | $5.12 | 1640 | 100.0% | 0 | 0 |
| PremiumCloud | $+572.49 | $+35.78 | 82.81 | 177.85 | 75.0% | 0.763 | $6.95 | 910 | 100.0% | 0 | 0 |
| SpotBroker | $+1383.89 | $+86.49 | 39.64 | 0.00 | 100.0% | 0.748 | $5.95 | 860 | 99.6% | 0 | 0 |

## 二、声誉三维分解

| Agent | 平均交付声誉 | 平均定价声誉 | 平均合作声誉 | 加权平均声誉 |
|---|---|---|---|---|
| Hyperscaler | 0.935 | 0.935 | 0.133 | 0.735 |
| PremiumCloud | 0.963 | 0.963 | 0.173 | 0.765 |
| SpotBroker | 0.913 | 0.916 | 0.102 | 0.711 |

## 三、逐轮关键记录

### Round 0 | 真实需求 181 | 观测需求 184 | 市场均价 $5.53

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 184 | $5.00 | 120 | 74.4 | 0.0 | $-133.77 | $-133.77 | 0.687 | 0/15 | Starting from fallback (70 units @ $4.20), raised price to $... |
| PremiumCloud | 184 | $6.60 | 100 | 37.3 | 0.0 | $-96.94 | $-96.94 | 0.799 | 0/15 | We set quantity to max legal limit (100) because observed de... |
| SpotBroker | 184 | $5.00 | 20 | 65.0 | 4.3 | $+61.46 | $+61.46 | 0.594 | 30/0 | No prior round to adjust from — this is round 0. We adopt th... |

### Round 1 | 真实需求 197 | 观测需求 195 | 市场均价 $5.67

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 195 | $5.20 | 110 | 79.1 | 0.0 | $-110.66 | $-244.44 | 0.703 | 0/0 | Reduced quantity from 120 to 110 to clear excess inventory (... |
| PremiumCloud | 195 | $6.60 | 80 | 43.6 | 0.0 | $-27.43 | $-124.37 | 0.790 | 0/4 | Reduced quantity from 100 to 80 to eliminate overstock and r... |
| SpotBroker | 195 | $5.20 | 70 | 74.3 | 0.0 | $+65.32 | $+126.78 | 0.633 | 4/0 | Increased quantity from 20 to 70 to eliminate shortage (last... |

### Round 2 | 真实需求 198 | 观测需求 197 | 市场均价 $5.93

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 79 | $5.20 | 80 | 92.8 | 0.0 | $+140.26 | $-104.18 | 0.715 | 0/0 | Reduced forecast from 195 → 80 (aggressive de-escalation to ... |
| PremiumCloud | 43 | $7.00 | 40 | 37.5 | 0.0 | $+102.95 | $-21.42 | 0.780 | 0/0 | Reduced forecast from 195 → 44 (applying forecast_bias −0.8 ... |
| SpotBroker | 194 | $5.60 | 80 | 67.7 | 0.0 | $+38.44 | $+165.22 | 0.662 | 0/0 | Raised price from $5.2 to $5.7 (+$0.5) to improve margin cov... |

### Round 3 | 真实需求 202 | 观测需求 204 | 市场均价 $6.00

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 84 | $5.20 | 90 | 98.9 | 0.0 | $+119.50 | $+15.32 | 0.724 | 0/0 | Raised price from 5.2 to 5.3 to improve margin, increased qu... |
| PremiumCloud | 34 | $7.00 | 30 | 38.9 | 0.0 | $+156.60 | $+135.18 | 0.772 | 0/0 | Reduced forecast_demand from 43 to 35 to better match histor... |
| SpotBroker | 204 | $5.80 | 70 | 64.1 | 0.0 | $+78.61 | $+243.83 | 0.684 | 0/0 | Reduced quantity from 80 to 70 to eliminate overstock (last ... |

### Round 4 | 真实需求 193 | 观测需求 194 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 204 | $5.40 | 110 | 87.7 | 0.0 | $-43.78 | $-28.46 | 0.730 | 0/0 | Raised price from 5.2 to 5.4 to improve margin; increased qu... |
| PremiumCloud | 202 | $7.00 | 100 | 38.9 | 0.0 | $-177.85 | $-42.67 | 0.767 | 0/0 | Increased quantity from 30 to 100 to capture massive observe... |
| SpotBroker | 181 | $5.80 | 60 | 66.4 | 0.0 | $+139.62 | $+383.45 | 0.701 | 0/0 | Reduced quantity from 70 to 60 to align with trailing realiz... |

### Round 5 | 真实需求 182 | 观测需求 183 | 市场均价 $6.20

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 201 | $5.60 | 110 | 80.2 | 0.0 | $-70.87 | $-99.33 | 0.735 | 0/0 | Raised price from 5.4 to 5.6 to capture margin upside amid s... |
| PremiumCloud | 205 | $7.00 | 40 | 40.4 | 0.0 | $+122.29 | $+79.62 | 0.763 | 0/0 | Reduced quantity from 100 to 40 to eliminate overproduction ... |
| SpotBroker | 174 | $6.00 | 60 | 61.5 | 0.0 | $+123.60 | $+507.05 | 0.713 | 0/0 | Reduced quantity from 60 to 65 to slightly increase coverage... |

### Round 6 | 真实需求 171 | 观测需求 175 | 市场均价 $6.13

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 83 | $5.20 | 80 | 90.7 | 0.0 | $+131.04 | $+31.71 | 0.739 | 0/0 | Reduced quantity by 30 (110→80) to match realized demand tre... |
| PremiumCloud | 187 | $7.00 | 40 | 34.2 | 0.0 | $+79.84 | $+159.46 | 0.759 | 0/0 | Reduced quantity from 40 to 40 (capped at recent realized de... |
| SpotBroker | 171 | $6.20 | 60 | 46.1 | 0.0 | $+38.84 | $+545.89 | 0.722 | 0/0 | Raised price from $6.0 to $6.2 (+$0.2) to capitalize on high... |

### Round 7 | 真实需求 194 | 观测需求 196 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 83 | $5.00 | 80 | 109.6 | 0.0 | $+184.73 | $+216.44 | 0.742 | 4/0 | Reduced quantity from 110 to 80 to match realized demand tre... |
| PremiumCloud | 195 | $7.00 | 40 | 35.6 | 0.0 | $+118.71 | $+278.17 | 0.761 | 0/4 | Held price at $7.0 (no change) to maintain premium positioni... |
| SpotBroker | 174 | $6.20 | 60 | 48.8 | 0.0 | $+54.22 | $+600.12 | 0.729 | 0/0 | Raised price by $0.1 (6.2→6.3) to capture volatility premium... |

### Round 8 | 真实需求 196 | 观测需求 187 | 市场均价 $6.13

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 109 | $5.20 | 110 | 103.9 | 0.0 | $+27.76 | $+244.20 | 0.744 | 0/0 | Increased quantity from 80 to 110 to address chronic under-f... |
| PremiumCloud | 188 | $7.00 | 50 | 38.7 | 0.0 | $+70.17 | $+348.34 | 0.758 | 0/0 | Reduced quantity from 40 to 36 to eliminate persistent surpl... |
| SpotBroker | 187 | $6.20 | 50 | 53.4 | 0.0 | $+129.03 | $+729.14 | 0.734 | 0/0 | Reduced quantity from 60 to 50 to match realized demand tren... |

### Round 9 | 真实需求 200 | 观测需求 198 | 市场均价 $6.20

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 192 | $5.40 | 120 | 99.0 | 0.0 | $-44.89 | $+199.31 | 0.745 | 0/0 | Raised price from 5.2 to 5.4 to improve margin resilience am... |
| PremiumCloud | 186 | $7.00 | 60 | 42.2 | 0.0 | $+48.91 | $+397.26 | 0.756 | 0/0 | Reduced quantity_bias from +6.0 to +2.0 (net quantity 46 vs ... |
| SpotBroker | 183 | $6.20 | 50 | 58.8 | 0.0 | $+164.05 | $+893.19 | 0.738 | 0/0 | Raised price from $6.2 to $6.3 to improve margin amid rising... |

### Round 10 | 真实需求 198 | 观测需求 198 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 192 | $5.00 | 100 | 111.8 | 0.0 | $+108.04 | $+307.35 | 0.746 | 0/0 | Reduced quantity sharply from 120 → 100 to eliminate overpro... |
| PremiumCloud | 194 | $7.00 | 60 | 35.9 | 0.0 | $+3.35 | $+400.60 | 0.755 | 0/0 | Reduced quantity from 60 to 50 to curb inventory decay and a... |
| SpotBroker | 196 | $6.20 | 60 | 50.3 | 0.0 | $+65.47 | $+958.66 | 0.741 | 0/0 | Increased quantity from 50 to 55 to match upward trend in re... |

### Round 11 | 真实需求 186 | 观测需求 183 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 182 | $5.00 | 100 | 105.0 | 0.0 | $+75.14 | $+382.49 | 0.747 | 0/0 | Cut quantity from 100→100 (no change) but lowered price from... |
| PremiumCloud | 194 | $7.00 | 60 | 33.6 | 0.0 | $-13.83 | $+386.78 | 0.753 | 0/0 | Reduced quantity from 60 to 50 to halt inventory buildup and... |
| SpotBroker | 193 | $6.20 | 60 | 47.4 | 0.0 | $+45.78 | $+1004.44 | 0.743 | 0/0 | Reduced quantity from 60 to 55 to cut leftover inventory (9.... |

### Round 12 | 真实需求 176 | 观测需求 178 | 市场均价 $6.00

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 101 | $4.80 | 100 | 105.4 | 0.0 | $+18.98 | $+401.47 | 0.748 | 5/0 | Raised price from $5.0 to $5.2 to comply with profit rule (a... |
| PremiumCloud | 33 | $7.00 | 40 | 29.2 | 0.0 | $+81.71 | $+468.49 | 0.757 | 0/5 | Slashed quantity from 60 to 30 to match actual demand; kept ... |
| SpotBroker | 178 | $6.20 | 50 | 41.4 | 0.0 | $+52.93 | $+1057.36 | 0.745 | 0/0 | Reduced price from $6.2 to $5.9 to stimulate demand capture ... |

### Round 13 | 真实需求 172 | 观测需求 181 | 市场均价 $5.93

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 101 | $4.80 | 100 | 99.4 | 0.0 | $+27.05 | $+428.52 | 0.749 | 0/0 | Reduced forecast from 101 (R12) to 105 to better match recen... |
| PremiumCloud | 35 | $7.00 | 40 | 27.6 | 0.0 | $+34.03 | $+502.52 | 0.755 | 0/0 | Reduced quantity from 40 to 30 to match realized demand tren... |
| SpotBroker | 180 | $6.00 | 40 | 45.0 | 0.0 | $+110.76 | $+1168.12 | 0.746 | 0/0 | Reduced quantity from 50 to 40 to match declining realized a... |

### Round 14 | 真实需求 190 | 观测需求 196 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 171 | $5.00 | 110 | 107.2 | 0.0 | $+24.26 | $+452.78 | 0.749 | 0/0 | Raised price from $4.8 to $5.2 to restore margin after profi... |
| PremiumCloud | 191 | $7.00 | 60 | 34.2 | 0.0 | $+40.87 | $+543.39 | 0.759 | 0/7 | Reduced quantity from 100 (fallback) to 50 to avoid R11-styl... |
| SpotBroker | 42 | $6.20 | 30 | 48.5 | 0.0 | $+136.43 | $+1304.56 | 0.747 | 7/0 | Increased quantity from 40 to 45 to correct chronic under-al... |

### Round 15 | 真实需求 197 | 观测需求 193 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 171 | $5.00 | 120 | 111.1 | 0.0 | $-22.10 | $+430.68 | 0.749 | 0/0 | Raised price from $5.0 to $5.2 to enforce margin floor after... |
| PremiumCloud | 187 | $7.00 | 70 | 35.6 | 0.0 | $+29.10 | $+572.49 | 0.763 | 0/10 | Kept price at $7.0 (no change) and held quantity at 60 (same... |
| SpotBroker | 40 | $6.20 | 40 | 50.3 | 0.0 | $+79.34 | $+1383.89 | 0.748 | 10/0 | Increased quantity from 30 to 50 to match stable realized de... |

## 四、利润演变

| Round | Hyp | Pre | Spo | 市场均价 |
|---|---|---|---|---|
| 0 | $-133.77 | $-96.94 | $+61.46 | $5.53 |
| 1 | $-110.66 | $-27.43 | $+65.32 | $5.67 |
| 2 | $+140.26 | $+102.95 | $+38.44 | $5.93 |
| 3 | $+119.50 | $+156.60 | $+78.61 | $6.00 |
| 4 | $-43.78 | $-177.85 | $+139.62 | $6.07 |
| 5 | $-70.87 | $+122.29 | $+123.60 | $6.20 |
| 6 | $+131.04 | $+79.84 | $+38.84 | $6.13 |
| 7 | $+184.73 | $+118.71 | $+54.22 | $6.07 |
| 8 | $+27.76 | $+70.17 | $+129.03 | $6.13 |
| 9 | $-44.89 | $+48.91 | $+164.05 | $6.20 |
| 10 | $+108.04 | $+3.35 | $+65.47 | $6.07 |
| 11 | $+75.14 | $-13.83 | $+45.78 | $6.07 |
| 12 | $+18.98 | $+81.71 | $+52.93 | $6.00 |
| 13 | $+27.05 | $+34.03 | $+110.76 | $5.93 |
| 14 | $+24.26 | $+40.87 | $+136.43 | $6.07 |
| 15 | $-22.10 | $+29.10 | $+79.34 | $6.07 |

### 累计利润演变

| Round | Hyp | Pre | Spo |
|---|---|---|---|---|
| 0 | $-133.77 | $-96.94 | $+61.46 |
| 1 | $-244.44 | $-124.37 | $+126.78 |
| 2 | $-104.18 | $-21.42 | $+165.22 |
| 3 | $+15.32 | $+135.18 | $+243.83 |
| 4 | $-28.46 | $-42.67 | $+383.45 |
| 5 | $-99.33 | $+79.62 | $+507.05 |
| 6 | $+31.71 | $+159.46 | $+545.89 |
| 7 | $+216.44 | $+278.17 | $+600.12 |
| 8 | $+244.20 | $+348.34 | $+729.14 |
| 9 | $+199.31 | $+397.26 | $+893.19 |
| 10 | $+307.35 | $+400.60 | $+958.66 |
| 11 | $+382.49 | $+386.78 | $+1004.44 |
| 12 | $+401.47 | $+468.49 | $+1057.36 |
| 13 | $+428.52 | $+502.52 | $+1168.12 |
| 14 | $+452.78 | $+543.39 | $+1304.56 |
| 15 | $+430.68 | $+572.49 | $+1383.89 |

## 五、策略调整关键词分析

### Hyperscaler
**margin** (10), **observed** (8), **realized** (8), **inventory** (7), **better** (6), **match** (6), **units** (5), **align** (5), **improve** (5), **risk** (5)

### PremiumCloud
**observed** (8), **inventory** (8), **legal** (7), **realized** (7), **kept** (6), **premium** (5), **positioning** (5), **avoid** (5), **match** (5), **sales** (5)

### SpotBroker
**realized** (8), **margin** (7), **inventory** (6), **above** (6), **observed** (5), **coverage** (5), **reputation** (5), **trend** (5), **match** (5), **cost** (4)

## 六、策略分化度

| 维度 | 观察 |
|---|---|
| **定价分化** | 最高均价 $6.95 (PremiumCloud) vs 最低 $5.12 (Hyperscaler)，价差 $1.83 |
| **产能分化** | 总进货量: Hyperscaler=1640 / PremiumCloud=910 / SpotBroker=860 |
| **利润路径** | Hyperscaler=$+430.68 / PremiumCloud=$+572.49 / SpotBroker=$+1383.89 |
| **声誉分化** | Hyperscaler=0.749 / PremiumCloud=0.763 / SpotBroker=0.748 |

## 七、结论

- **赢家**: SpotBroker，累计利润 $+1383.89
- **末位**: Hyperscaler，累计利润 $+430.68
- **定价策略分化**: 价差 $1.83，说明角色设定得到有效维持
- **盈利稳定性**: 三 Agent 平均胜率 79.2%
