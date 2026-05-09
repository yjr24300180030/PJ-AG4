# Branch 3: 强约束最优 (Heavily Constrained Optimal) — 详细实验报告

**实验描述**: 完整利润安全网 + 数量上限 + 保守销售估计，标准进化限制，收敛到高价少货范式
**总轮数**: 30
**模型**: qwen-plus (阿里云百炼)

## 一、核心指标总览

| Agent | 累计利润 | 平均轮利润 | 利润波动 | 最大回撤 | 胜率 | 最终声誉 | 平均定价 | 总进货量 | 平均服务率 | 倾销次数 | 违约次数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | $+3161.06 | $+105.37 | 55.54 | 47.34 | 96.7% | 0.763 | $5.79 | 2420 | 98.0% | 0 | 2 |
| PremiumCloud | $+3326.45 | $+110.88 | 83.37 | 107.52 | 86.7% | 0.839 | $6.97 | 1690 | 99.7% | 0 | 0 |
| SpotBroker | $+2956.26 | $+98.54 | 32.36 | 0.00 | 100.0% | 0.707 | $5.97 | 1710 | 97.9% | 0 | 2 |

## 二、声誉三维分解

| Agent | 平均交付声誉 | 平均定价声誉 | 平均合作声誉 | 加权平均声誉 |
|---|---|---|---|---|
| Hyperscaler | 0.959 | 0.965 | 0.211 | 0.774 |
| PremiumCloud | 0.979 | 0.980 | 0.221 | 0.790 |
| SpotBroker | 0.945 | 0.955 | 0.055 | 0.726 |

## 三、逐轮关键记录

### Round 0 | 真实需求 181 | 观测需求 184 | 市场均价 $5.53

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 184 | $5.00 | 80 | 74.4 | 0.0 | $+111.73 | $+111.73 | 0.701 | 0/15 | Starting from fallback (70 units @ $4.20), raised price to $... |
| PremiumCloud | 184 | $6.60 | 100 | 37.3 | 0.0 | $-96.94 | $-96.94 | 0.799 | 0/15 | We set quantity to max legal limit (100) because observed de... |
| SpotBroker | 184 | $5.00 | 20 | 65.0 | 4.3 | $+61.46 | $+61.46 | 0.594 | 30/0 | We set quantity to 20 (up from fallback 20 — no change), pri... |

### Round 1 | 真实需求 197 | 观测需求 195 | 市场均价 $5.67

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 195 | $5.20 | 90 | 79.9 | 0.0 | $+20.44 | $+132.16 | 0.713 | 0/0 | Raised price from $5.0 to $5.4 to meet $0.50 risk margin; ke... |
| PremiumCloud | 195 | $6.60 | 80 | 43.3 | 0.0 | $-32.90 | $-129.84 | 0.789 | 0/4 | Reduced quantity from 100 to 80 to eliminate overproduction ... |
| SpotBroker | 195 | $5.20 | 70 | 73.8 | 0.0 | $+66.18 | $+127.64 | 0.633 | 4/0 | Increased quantity from 20 to 70 to eliminate chronic shorta... |

### Round 2 | 真实需求 198 | 观测需求 197 | 市场均价 $6.00

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 198 | $5.20 | 90 | 97.7 | 0.0 | $+115.15 | $+247.31 | 0.723 | 0/0 | Held price at $5.20 (same as Round 1) and quantity at 90 (sa... |
| PremiumCloud | 197 | $7.00 | 80 | 39.0 | 0.0 | $-74.62 | $-204.46 | 0.779 | 0/0 | Reduced quantity from 100 (Round 0) and held at 80 (Round 1)... |
| SpotBroker | 200 | $5.80 | 70 | 61.3 | 0.0 | $+62.97 | $+190.61 | 0.662 | 0/0 | Raised price from 5.2 to 5.8 (+0.6) to improve margin and al... |

### Round 3 | 真实需求 202 | 观测需求 204 | 市场均价 $5.93

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 200 | $5.20 | 90 | 94.9 | 0.0 | $+101.41 | $+348.72 | 0.729 | 0/0 | Raised quantity by 10 (90→100) to address prior under-alloca... |
| PremiumCloud | 192 | $7.00 | 60 | 37.0 | 0.0 | $+32.07 | $-172.39 | 0.774 | 0/3 | Reduced quantity from 80 to 60 to match actual demand (~39) ... |
| SpotBroker | 196 | $5.60 | 60 | 70.1 | 0.0 | $+123.49 | $+314.10 | 0.684 | 3/0 | Reduced quantity from 70 to 65 to eliminate surplus and hold... |

### Round 4 | 真实需求 193 | 观测需求 194 | 市场均价 $5.93

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 203 | $5.20 | 90 | 90.3 | 0.0 | $+77.88 | $+426.60 | 0.735 | 0/0 | Raised price from 5.2 to 5.3 to improve margin resilience af... |
| PremiumCloud | 188 | $7.00 | 50 | 34.7 | 0.0 | $+96.71 | $-75.68 | 0.773 | 0/8 | Reduced quantity from 60 to 50 to cut production cost and ma... |
| SpotBroker | 190 | $5.60 | 60 | 68.0 | 0.0 | $+77.26 | $+391.36 | 0.701 | 8/0 | Reduced quantity from 60 → 65 to better cover recent realize... |

### Round 5 | 真实需求 182 | 观测需求 183 | 市场均价 $5.93

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 199 | $5.20 | 90 | 84.9 | 0.0 | $+48.95 | $+475.55 | 0.738 | 0/0 | Raised quantity from 90 to 94 (+4) to better match recent de... |
| PremiumCloud | 182 | $7.00 | 40 | 32.4 | 0.0 | $+101.35 | $+25.67 | 0.771 | 0/5 | Reduced quantity from 50 to 45 to shrink inventory buildup a... |
| SpotBroker | 186 | $5.60 | 60 | 64.7 | 0.0 | $+82.90 | $+474.25 | 0.713 | 5/0 | Raised price by $0.10 (5.6→5.7) to improve margin amid risin... |

### Round 6 | 真实需求 171 | 观测需求 175 | 市场均价 $6.13

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 179 | $5.80 | 80 | 62.2 | 0.0 | $+21.61 | $+497.16 | 0.741 | 0/0 | Cut quantity from 90 to 85 to match demand decay trend and r... |
| PremiumCloud | 172 | $7.00 | 50 | 35.8 | 0.0 | $+144.48 | $+170.16 | 0.776 | 0/13 | Raised price from $7.0 to $7.15 (+0.15) to capture margin ex... |
| SpotBroker | 178 | $5.60 | 60 | 73.0 | 0.0 | $+68.53 | $+542.79 | 0.722 | 13/0 | Raised price from 5.6 to 5.7 to improve margin resilience am... |

### Round 7 | 真实需求 194 | 观测需求 196 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 169 | $6.00 | 70 | 72.1 | 0.0 | $+146.77 | $+643.93 | 0.744 | 0/0 | Reduced quantity from 80 to 70 to cut overstock; raised pric... |
| PremiumCloud | 162 | $7.00 | 50 | 47.9 | 0.0 | $+164.90 | $+335.06 | 0.774 | 0/4 | Hold price at $7.0 (legal ceiling), reduce quantity from 50→... |
| SpotBroker | 170 | $6.00 | 70 | 74.0 | 0.0 | $+123.34 | $+666.13 | 0.729 | 4/0 | Raised quantity from 60 to 70 to match rising realized sales... |

### Round 8 | 真实需求 196 | 观测需求 187 | 市场均价 $6.00

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 189 | $5.00 | 120 | 106.4 | 0.0 | $-47.34 | $+596.59 | 0.745 | 0/0 | nan |
| PremiumCloud | 177 | $7.00 | 60 | 35.0 | 0.0 | $-1.90 | $+333.16 | 0.768 | 0/0 | Raised price by $0.15 (from $7.0 to $7.15) to capture margin... |
| SpotBroker | 179 | $6.00 | 70 | 54.6 | 0.0 | $+34.27 | $+700.40 | 0.734 | 0/0 | Raised price by $0.2 (from 6.0) to boost margin; held quanti... |

### Round 9 | 真实需求 200 | 观测需求 198 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 193 | $6.00 | 90 | 74.3 | 0.0 | $+49.65 | $+646.24 | 0.746 | 0/0 | Raised quantity from 70 to 100 to capture pent-up demand sig... |
| PremiumCloud | 181 | $7.00 | 50 | 48.7 | 0.0 | $+252.10 | $+585.25 | 0.781 | 0/15 | Reduced quantity from 60 to 45 to match realized demand vola... |
| SpotBroker | 174 | $6.00 | 50 | 77.1 | 0.0 | $+151.76 | $+852.16 | 0.738 | 15/0 | Reduced quantity from 70 to 60 to eliminate surplus risk (R8... |

### Round 10 | 真实需求 198 | 观测需求 198 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 195 | $6.00 | 100 | 73.2 | 0.0 | $+78.35 | $+724.58 | 0.765 | 0/15 | Increased quantity from 90 (R9) to 95 to better match observ... |
| PremiumCloud | 192 | $7.00 | 60 | 48.7 | 0.0 | $+105.03 | $+690.28 | 0.775 | 0/1 | Reduced quantity from 50 (R9) to 48 to match realized demand... |
| SpotBroker | 180 | $6.00 | 60 | 76.2 | 0.0 | $+109.12 | $+961.28 | 0.741 | 16/0 | Reduced forecast from fallback 199 to 187 (applying -7 forec... |

### Round 11 | 真实需求 186 | 观测需求 183 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 196 | $6.00 | 100 | 69.7 | 0.0 | $+56.97 | $+781.55 | 0.777 | 0/15 | Increased quantity from 100 to 110 to better match observed ... |
| PremiumCloud | 191 | $7.00 | 60 | 45.0 | 0.0 | $+116.73 | $+807.01 | 0.777 | 0/6 | Reduced quantity from 60 to 50 to align with stable realized... |
| SpotBroker | 166 | $6.00 | 50 | 71.2 | 0.0 | $+87.08 | $+1048.36 | 0.743 | 21/0 | Reduced forecast by 7 (180→173) per evolution bias; held qua... |

### Round 12 | 真实需求 176 | 观测需求 178 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 172 | $6.00 | 80 | 66.5 | 0.0 | $+102.40 | $+883.96 | 0.780 | 0/7 | Reduced quantity from 100 to 75 to match realized demand tre... |
| PremiumCloud | 170 | $7.00 | 50 | 42.4 | 0.0 | $+97.56 | $+904.57 | 0.770 | 0/0 | Reduced quantity from 60 to 50 to directly address inventory... |
| SpotBroker | 166 | $6.00 | 60 | 67.1 | 0.0 | $+113.07 | $+1161.42 | 0.745 | 7/0 | Increased quantity from 50 to 70 to better match realized de... |

### Round 13 | 真实需求 172 | 观测需求 181 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 166 | $6.00 | 80 | 65.2 | 0.0 | $+85.90 | $+969.85 | 0.781 | 0/6 | Reduced quantity from 80 to 75 to better match recent realiz... |
| PremiumCloud | 166 | $7.00 | 40 | 41.1 | 0.0 | $+132.39 | $+1036.96 | 0.765 | 0/0 | Reduced quantity from 50 to 40 to align with declining reali... |
| SpotBroker | 169 | $6.00 | 60 | 65.7 | 0.0 | $+113.49 | $+1274.91 | 0.746 | 6/0 | Increased quantity from 60 to 70 to match improving stock co... |

### Round 14 | 真实需求 190 | 观测需求 196 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 164 | $6.00 | 70 | 79.6 | 0.0 | $+227.54 | $+1197.39 | 0.791 | 0/6 | Reduced quantity from 80 to 70 to match realized demand tren... |
| PremiumCloud | 180 | $7.00 | 100 | 49.8 | 0.0 | $+12.58 | $+1049.54 | 0.774 | 0/15 | nan |
| SpotBroker | 168 | $6.40 | 40 | 60.6 | 0.0 | $+85.50 | $+1360.41 | 0.747 | 21/0 | Reduced quantity from 60 to 50 to align with recent realized... |

### Round 15 | 真实需求 197 | 观测需求 193 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 185 | $6.00 | 80 | 82.8 | 0.0 | $+160.07 | $+1357.47 | 0.781 | 0/0 | Increased quantity from 70 to 85 to better capture observed ... |
| PremiumCloud | 190 | $7.00 | 60 | 51.7 | 0.0 | $+134.31 | $+1183.84 | 0.771 | 0/2 | Increased quantity from 40 (R13) to 55 — a +15 unit adjustme... |
| SpotBroker | 152 | $6.40 | 60 | 62.4 | 0.0 | $+136.90 | $+1497.31 | 0.748 | 2/0 | Raised quantity from 40 to 55 to cut transfer costs; held pr... |

### Round 16 | 真实需求 198 | 观测需求 197 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 186 | $6.00 | 80 | 82.7 | 0.0 | $+160.01 | $+1517.48 | 0.773 | 0/0 | Increased quantity from 80 to 85 to better capture rising re... |
| PremiumCloud | 189 | $7.00 | 60 | 52.1 | 0.0 | $+217.54 | $+1401.38 | 0.782 | 0/13 | Increased quantity from 60 to 65 to improve fill rate and re... |
| SpotBroker | 142 | $6.40 | 50 | 63.2 | 0.0 | $+107.49 | $+1604.80 | 0.748 | 13/0 | Lowered price from $6.4 to $6.0 to boost allocation share an... |

### Round 17 | 真实需求 194 | 观测需求 195 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 187 | $6.00 | 80 | 80.3 | 0.0 | $+145.71 | $+1663.19 | 0.767 | 0/0 | Increased quantity from 80 to 85 to align with strong observ... |
| PremiumCloud | 192 | $7.00 | 60 | 51.7 | 0.0 | $+132.59 | $+1533.97 | 0.777 | 0/2 | Increased quantity from 60 to 65 to better align with observ... |
| SpotBroker | 142 | $6.40 | 60 | 61.9 | 0.0 | $+137.35 | $+1742.15 | 0.749 | 2/0 | Raised quantity from 50 to 60 to cut transfer dependency; he... |

### Round 18 | 真实需求 173 | 观测需求 168 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 175 | $6.00 | 80 | 71.4 | 0.0 | $+91.25 | $+1754.44 | 0.763 | 0/0 | Reduced quantity from 80 to 75 to align with declining reali... |
| PremiumCloud | 184 | $7.00 | 50 | 46.1 | 0.0 | $+123.99 | $+1657.96 | 0.770 | 0/0 | Reduced quantity from 60 to 50 to align with realized demand... |
| SpotBroker | 156 | $6.40 | 60 | 55.5 | 0.0 | $+109.77 | $+1851.92 | 0.749 | 0/0 | Increased quantity from 60 to 65 to better match realized de... |

### Round 19 | 真实需求 160 | 观测需求 166 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 163 | $6.00 | 70 | 66.0 | 0.0 | $+110.92 | $+1865.36 | 0.760 | 0/0 | Reduced quantity from 80 to 70 to align with declining reali... |
| PremiumCloud | 158 | $7.00 | 50 | 42.4 | 0.0 | $+98.52 | $+1756.48 | 0.765 | 0/0 | Reduced quantity from 50 → 52 (to match realized demand ceil... |
| SpotBroker | 164 | $6.40 | 60 | 51.6 | 0.0 | $+83.51 | $+1935.43 | 0.749 | 0/0 | Raised quantity from 60 to 63 to better match recent realize... |

### Round 20 | 真实需求 160 | 观测需求 161 | 市场均价 $6.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 149 | $6.00 | 60 | 65.9 | 0.0 | $+161.31 | $+2026.67 | 0.757 | 0/0 | Reduced quantity from 70 to 65 to match observed demand deca... |
| PremiumCloud | 153 | $7.00 | 50 | 42.3 | 0.0 | $+97.56 | $+1854.04 | 0.761 | 0/0 | Reduced forecast_demand from 158 to 157 to better track the ... |
| SpotBroker | 149 | $6.40 | 60 | 51.7 | 0.0 | $+83.84 | $+2019.27 | 0.750 | 0/0 | Increased quantity from 60 to 63 to better track upward drif... |

### Round 21 | 真实需求 182 | 观测需求 175 | 市场均价 $6.40

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 159 | $6.00 | 80 | 71.5 | 0.0 | $+91.47 | $+2118.13 | 0.756 | 0/0 | Increased quantity from 60 to 66 to align with persistent re... |
| PremiumCloud | 163 | $7.00 | 40 | 45.8 | 0.0 | $+173.78 | $+2027.83 | 0.761 | 0/1 | Reduced quantity from 50 to 43 to match realized demand (~42... |
| SpotBroker | 140 | $6.20 | 50 | 64.7 | 0.0 | $+193.84 | $+2213.11 | 0.750 | 1/0 | Reduced quantity from 60 to 52 to match realized demand (~51... |

### Round 22 | 真实需求 198 | 观测需求 205 | 市场均价 $6.40

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 159 | $6.00 | 80 | 77.7 | 0.0 | $+194.19 | $+2312.32 | 0.817 | 0/10 | Increased quantity from 80 to 85 to test demand resilience a... |
| PremiumCloud | 163 | $7.00 | 40 | 49.9 | 0.0 | $+249.29 | $+2277.12 | 0.821 | 0/7 | Increased quantity from 40 to 43 to restore stock coverage a... |
| SpotBroker | 120 | $6.20 | 50 | 67.3 | 3.2 | $+96.68 | $+2309.79 | 0.745 | 17/0 | Reduced forecast from 140 to 130 to correct persistent over-... |

### Round 23 | 真实需求 188 | 观测需求 186 | 市场均价 $6.40

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 190 | $6.00 | 90 | 75.8 | 0.0 | $+148.94 | $+2461.26 | 0.860 | 0/14 | Increased quantity from 80 to 90 to test latent demand resil... |
| PremiumCloud | 181 | $7.00 | 50 | 48.6 | 0.0 | $+145.00 | $+2422.12 | 0.803 | 0/0 | Increased forecast from 163 to 187 to correct prior under-fo... |
| SpotBroker | 166 | $6.20 | 50 | 63.6 | 0.0 | $+108.64 | $+2418.43 | 0.746 | 14/0 | Reduced forecast from 202 (fallback) to 176 to reflect obser... |

### Round 24 | 真实需求 187 | 观测需求 183 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 180 | $6.00 | 80 | 74.4 | 0.0 | $+119.06 | $+2580.32 | 0.848 | 0/1 | Reduced quantity from 90 to 80 to eliminate overstock risk a... |
| PremiumCloud | 163 | $7.00 | 50 | 44.3 | 0.0 | $+165.26 | $+2587.38 | 0.852 | 0/7 | Reduced quantity from 50 to 49 to eliminate marginal holding... |
| SpotBroker | 183 | $6.00 | 60 | 68.3 | 0.0 | $+105.58 | $+2524.01 | 0.747 | 8/0 | Raised quantity from 50 to 74 to match forecast bias-correct... |

### Round 25 | 真实需求 181 | 观测需求 181 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 174 | $6.00 | 80 | 70.3 | 0.0 | $+119.98 | $+2700.30 | 0.850 | 0/6 | Reduced quantity from 80 to 75 to eliminate holding/obsolesc... |
| PremiumCloud | 163 | $7.00 | 50 | 45.1 | 0.0 | $+120.25 | $+2707.64 | 0.827 | 0/0 | Reduced quantity from 50 to 49 to eliminate holding/obsolesc... |
| SpotBroker | 181 | $6.00 | 60 | 65.6 | 0.0 | $+113.53 | $+2637.54 | 0.748 | 6/0 | Raised quantity from 60 to 74 to better match forecast (193)... |

### Round 26 | 真实需求 163 | 观测需求 167 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 162 | $6.00 | 70 | 63.9 | 0.0 | $+98.29 | $+2798.59 | 0.825 | 0/0 | Reduced quantity from 80 to 70 to halt inventory accumulatio... |
| PremiumCloud | 163 | $7.00 | 50 | 39.6 | 0.0 | $+81.00 | $+2788.64 | 0.808 | 0/0 | Reduced quantity from 50 to 49 to eliminate marginal holding... |
| SpotBroker | 167 | $6.00 | 60 | 59.5 | 0.0 | $+111.87 | $+2749.41 | 0.748 | 0/0 | Raised quantity from 60 to 70 to better match demand surge a... |

### Round 27 | 真实需求 179 | 观测需求 184 | 市场均价 $6.27

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 142 | $6.00 | 60 | 65.6 | 0.0 | $+179.84 | $+2978.43 | 0.869 | 0/3 | Reduced quantity from 70 to 65 to better match demand contra... |
| PremiumCloud | 143 | $7.00 | 50 | 41.0 | 0.0 | $+201.57 | $+2990.22 | 0.839 | 0/15 | Reduced quantity from 50 to 48 to align with downward trend ... |
| SpotBroker | 167 | $5.80 | 50 | 68.6 | 3.8 | $+62.69 | $+2812.10 | 0.744 | 18/0 | Reduced quantity from 60 to 50 to match demand decline and a... |

### Round 28 | 真实需求 206 | 观测需求 208 | 市场均价 $6.27

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 118 | $6.00 | 60 | 60.0 | 17.6 | $+104.94 | $+3083.37 | 0.816 | 0/0 | Reduced forecast from 142 to 128 (applying -10.0 bias) to be... |
| PremiumCloud | 123 | $7.00 | 50 | 47.7 | 0.0 | $+187.74 | $+3177.96 | 0.879 | 0/7 | Reduced quantity from 50 to 48 to align with falling realize... |
| SpotBroker | 167 | $5.80 | 50 | 56.6 | 24.1 | $+48.41 | $+2860.51 | 0.715 | 7/0 | Reduced quantity from 50→50 (no change) but raised price fro... |

### Round 29 | 真实需求 218 | 观测需求 212 | 市场均价 $6.27

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 98 | $6.00 | 50 | 50.0 | 29.0 | $+77.68 | $+3161.06 | 0.763 | 0/0 | Reduced forecast from 118→108 to better match realized deman... |
| PremiumCloud | 103 | $7.00 | 50 | 50.0 | 4.3 | $+148.49 | $+3326.45 | 0.839 | 0/0 | Reduced quantity from 50 to 48 to prevent surplus amid decli... |
| SpotBroker | 200 | $5.80 | 70 | 70.0 | 14.6 | $+95.76 | $+2956.26 | 0.707 | 0/0 | Reduced quantity from 80 to 70 to avoid overstock and align ... |

## 四、利润演变

| Round | Hyp | Pre | Spo | 市场均价 |
|---|---|---|---|---|
| 0 | $+111.73 | $-96.94 | $+61.46 | $5.53 |
| 1 | $+20.44 | $-32.90 | $+66.18 | $5.67 |
| 2 | $+115.15 | $-74.62 | $+62.97 | $6.00 |
| 3 | $+101.41 | $+32.07 | $+123.49 | $5.93 |
| 4 | $+77.88 | $+96.71 | $+77.26 | $5.93 |
| 5 | $+48.95 | $+101.35 | $+82.90 | $5.93 |
| 6 | $+21.61 | $+144.48 | $+68.53 | $6.13 |
| 7 | $+146.77 | $+164.90 | $+123.34 | $6.33 |
| 8 | $-47.34 | $-1.90 | $+34.27 | $6.00 |
| 9 | $+49.65 | $+252.10 | $+151.76 | $6.33 |
| 10 | $+78.35 | $+105.03 | $+109.12 | $6.33 |
| 11 | $+56.97 | $+116.73 | $+87.08 | $6.33 |
| 12 | $+102.40 | $+97.56 | $+113.07 | $6.33 |
| 13 | $+85.90 | $+132.39 | $+113.49 | $6.33 |
| 14 | $+227.54 | $+12.58 | $+85.50 | $6.47 |
| 15 | $+160.07 | $+134.31 | $+136.90 | $6.47 |
| 16 | $+160.01 | $+217.54 | $+107.49 | $6.47 |
| 17 | $+145.71 | $+132.59 | $+137.35 | $6.47 |
| 18 | $+91.25 | $+123.99 | $+109.77 | $6.47 |
| 19 | $+110.92 | $+98.52 | $+83.51 | $6.47 |
| 20 | $+161.31 | $+97.56 | $+83.84 | $6.47 |
| 21 | $+91.47 | $+173.78 | $+193.84 | $6.40 |
| 22 | $+194.19 | $+249.29 | $+96.68 | $6.40 |
| 23 | $+148.94 | $+145.00 | $+108.64 | $6.40 |
| 24 | $+119.06 | $+165.26 | $+105.58 | $6.33 |
| 25 | $+119.98 | $+120.25 | $+113.53 | $6.33 |
| 26 | $+98.29 | $+81.00 | $+111.87 | $6.33 |
| 27 | $+179.84 | $+201.57 | $+62.69 | $6.27 |
| 28 | $+104.94 | $+187.74 | $+48.41 | $6.27 |
| 29 | $+77.68 | $+148.49 | $+95.76 | $6.27 |

### 累计利润演变

| Round | Hyp | Pre | Spo |
|---|---|---|---|---|
| 0 | $+111.73 | $-96.94 | $+61.46 |
| 1 | $+132.16 | $-129.84 | $+127.64 |
| 2 | $+247.31 | $-204.46 | $+190.61 |
| 3 | $+348.72 | $-172.39 | $+314.10 |
| 4 | $+426.60 | $-75.68 | $+391.36 |
| 5 | $+475.55 | $+25.67 | $+474.25 |
| 6 | $+497.16 | $+170.16 | $+542.79 |
| 7 | $+643.93 | $+335.06 | $+666.13 |
| 8 | $+596.59 | $+333.16 | $+700.40 |
| 9 | $+646.24 | $+585.25 | $+852.16 |
| 10 | $+724.58 | $+690.28 | $+961.28 |
| 11 | $+781.55 | $+807.01 | $+1048.36 |
| 12 | $+883.96 | $+904.57 | $+1161.42 |
| 13 | $+969.85 | $+1036.96 | $+1274.91 |
| 14 | $+1197.39 | $+1049.54 | $+1360.41 |
| 15 | $+1357.47 | $+1183.84 | $+1497.31 |
| 16 | $+1517.48 | $+1401.38 | $+1604.80 |
| 17 | $+1663.19 | $+1533.97 | $+1742.15 |
| 18 | $+1754.44 | $+1657.96 | $+1851.92 |
| 19 | $+1865.36 | $+1756.48 | $+1935.43 |
| 20 | $+2026.67 | $+1854.04 | $+2019.27 |
| 21 | $+2118.13 | $+2027.83 | $+2213.11 |
| 22 | $+2312.32 | $+2277.12 | $+2309.79 |
| 23 | $+2461.26 | $+2422.12 | $+2418.43 |
| 24 | $+2580.32 | $+2587.38 | $+2524.01 |
| 25 | $+2700.30 | $+2707.64 | $+2637.54 |
| 26 | $+2798.59 | $+2788.64 | $+2749.41 |
| 27 | $+2978.43 | $+2990.22 | $+2812.10 |
| 28 | $+3083.37 | $+3177.96 | $+2860.51 |
| 29 | $+3161.06 | $+3326.45 | $+2956.26 |

## 五、策略调整关键词分析

### Hyperscaler
**observed** (19), **realized** (18), **margin** (17), **match** (12), **better** (11), **inventory** (9), **align** (8), **while** (8), **improve** (8), **recent** (6)

### PremiumCloud
**margin** (15), **realized** (15), **inventory** (13), **observed** (12), **premium** (11), **reputation** (11), **kept** (10), **match** (10), **bias** (10), **signal** (8)

### SpotBroker
**margin** (17), **observed** (12), **market** (12), **improve** (11), **realized** (11), **bias** (10), **match** (10), **rising** (9), **better** (9), **transfer** (9)

## 六、策略分化度

| 维度 | 观察 |
|---|---|
| **定价分化** | 最高均价 $6.97 (PremiumCloud) vs 最低 $5.79 (Hyperscaler)，价差 $1.18 |
| **产能分化** | 总进货量: Hyperscaler=2420 / PremiumCloud=1690 / SpotBroker=1710 |
| **利润路径** | Hyperscaler=$+3161.06 / PremiumCloud=$+3326.45 / SpotBroker=$+2956.26 |
| **声誉分化** | Hyperscaler=0.763 / PremiumCloud=0.839 / SpotBroker=0.707 |

## 七、结论

- **赢家**: PremiumCloud，累计利润 $+3326.45
- **末位**: SpotBroker，累计利润 $+2956.26
- **定价策略分化**: 价差 $1.18，说明角色设定得到有效维持
- **盈利稳定性**: 三 Agent 平均胜率 94.4%
