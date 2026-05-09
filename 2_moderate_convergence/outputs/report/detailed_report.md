# Branch 2: 适度收敛 (Moderate Convergence) — 详细实验报告

**实验描述**: 中等约束，有成本安全网，无数量上限/利润安全网，标准进化限制
**总轮数**: 16
**模型**: qwen-plus (阿里云百炼)

## 一、核心指标总览

| Agent | 累计利润 | 平均轮利润 | 利润波动 | 最大回撤 | 胜率 | 最终声誉 | 平均定价 | 总进货量 | 平均服务率 | 倾销次数 | 违约次数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | $+1599.21 | $+99.95 | 65.76 | 88.52 | 93.8% | 0.727 | $5.78 | 1100 | 97.3% | 0 | 2 |
| PremiumCloud | $+1852.00 | $+115.75 | 98.96 | 136.24 | 87.5% | 0.771 | $6.66 | 870 | 95.4% | 0 | 3 |
| SpotBroker | $+1781.03 | $+111.31 | 57.40 | 0.00 | 100.0% | 0.884 | $5.96 | 1050 | 98.6% | 0 | 1 |

## 二、声誉三维分解

| Agent | 平均交付声誉 | 平均定价声誉 | 平均合作声誉 | 加权平均声誉 |
|---|---|---|---|---|
| Hyperscaler | 0.923 | 0.935 | 0.206 | 0.748 |
| PremiumCloud | 0.929 | 0.963 | 0.237 | 0.768 |
| SpotBroker | 0.904 | 0.916 | 0.268 | 0.750 |

## 三、逐轮关键记录

### Round 0 | 真实需求 181 | 观测需求 184 | 市场均价 $5.47

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 184 | $4.80 | 80 | 80.6 | 0.0 | $+124.32 | $+124.32 | 0.707 | 0/15 | Starting from fallback (70 units, $4.20), raised price to $4... |
| PremiumCloud | 184 | $6.60 | 100 | 35.1 | 0.0 | $-111.48 | $-111.48 | 0.799 | 0/15 | This is Round 0 — no prior action to adjust from. We start w... |
| SpotBroker | 184 | $5.00 | 20 | 65.0 | 0.3 | $+69.85 | $+69.85 | 0.600 | 30/0 | Upgraded forecast from fallback 55 to observed demand 184 to... |

### Round 1 | 真实需求 197 | 观测需求 195 | 市场均价 $5.73

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 195 | $5.20 | 110 | 82.4 | 0.0 | $-88.52 | $+35.80 | 0.718 | 0/0 | Raised price from 4.8 to 5.2 to ensure minimum $0.50 margin ... |
| PremiumCloud | 195 | $6.80 | 90 | 38.5 | 0.0 | $-136.24 | $-247.73 | 0.786 | 0/0 | Reduced quantity from 100 to 90 to eliminate inventory overh... |
| SpotBroker | 195 | $5.20 | 80 | 76.1 | 0.0 | $+56.07 | $+125.92 | 0.637 | 0/0 | Increased quantity from 20 to 80 to eliminate shortage (last... |

### Round 2 | 真实需求 198 | 观测需求 197 | 市场均价 $5.87

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 194 | $5.20 | 80 | 91.0 | 0.0 | $+134.62 | $+170.42 | 0.726 | 0/0 | Reduced quantity from 110 to 90 to cut overstock and holding... |
| PremiumCloud | 36 | $6.80 | 20 | 41.4 | 0.0 | $+202.77 | $-44.96 | 0.777 | 0/0 | Slashed quantity from 90 → 40 to eliminate inventory overhan... |
| SpotBroker | 191 | $5.60 | 80 | 65.6 | 0.0 | $+25.84 | $+151.76 | 0.665 | 0/0 | Reduced quantity from 80 to 75 to cut holding/obsolescence c... |

### Round 3 | 真实需求 202 | 观测需求 204 | 市场均价 $6.00

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 190 | $5.60 | 80 | 78.7 | 0.0 | $+102.55 | $+272.97 | 0.732 | 0/0 | Reduced quantity from 80 to 90 to better match rising realiz... |
| PremiumCloud | 38 | $6.80 | 20 | 46.4 | 0.0 | $+240.87 | $+195.92 | 0.770 | 0/0 | Reduced forecast from 36 (last round) to 42 — aligning with ... |
| SpotBroker | 191 | $5.60 | 70 | 76.9 | 0.0 | $+138.66 | $+290.42 | 0.687 | 0/0 | Reduced quantity from 80 to 70 to align with realized demand... |

### Round 4 | 真实需求 193 | 观测需求 194 | 市场均价 $6.20

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 185 | $6.00 | 80 | 66.2 | 0.0 | $+58.03 | $+331.00 | 0.736 | 0/0 | Raised price from $5.6 to $5.8 (+$0.2) to capture margin upl... |
| PremiumCloud | 200 | $6.80 | 50 | 50.9 | 0.0 | $+149.07 | $+344.98 | 0.765 | 0/0 | Increased quantity from 20 to 50 (+30) to capture latent dem... |
| SpotBroker | 194 | $5.80 | 80 | 75.9 | 0.0 | $+99.50 | $+389.92 | 0.702 | 0/0 | Reduced price from 5.6 to 5.4 to reverse R2–R3 profit collap... |

### Round 5 | 真实需求 182 | 观测需求 183 | 市场均价 $6.13

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 180 | $6.00 | 80 | 60.0 | 0.0 | $+18.55 | $+349.54 | 0.740 | 0/0 | Reduced quantity from 80 to 75 to better match recent realiz... |
| PremiumCloud | 193 | $6.60 | 50 | 52.4 | 0.0 | $+149.43 | $+494.42 | 0.762 | 0/0 | Increased price from 6.8 to 6.9 to capture margin uplift as ... |
| SpotBroker | 185 | $5.80 | 80 | 69.6 | 0.0 | $+62.15 | $+452.07 | 0.714 | 0/0 | Reduced price from 5.8 to 5.7 to counter slight demand softe... |

### Round 6 | 真实需求 171 | 观测需求 175 | 市场均价 $6.20

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 166 | $5.80 | 50 | 67.3 | 0.0 | $+201.22 | $+550.76 | 0.742 | 0/0 | Cut quantity from 80 to 60 to match falling realized demand ... |
| PremiumCloud | 48 | $6.80 | 40 | 44.0 | 0.0 | $+146.85 | $+641.27 | 0.759 | 0/0 | Raised price by $0.30 (from $6.6) to restore unit profit; he... |
| SpotBroker | 181 | $6.00 | 70 | 59.7 | 0.0 | $+63.30 | $+515.38 | 0.723 | 0/0 | Reduced quantity from 80 to 70 to match falling realized dem... |

### Round 7 | 真实需求 194 | 观测需求 196 | 市场均价 $6.27

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 153 | $5.80 | 60 | 79.9 | 0.0 | $+156.83 | $+707.60 | 0.744 | 11/0 | Raised quantity from 50 to 70 to better match recent realize... |
| PremiumCloud | 45 | $6.80 | 40 | 50.6 | 1.3 | $+154.26 | $+795.53 | 0.754 | 6/0 | Reduced forecast from 48→49 (aligning with recent realized d... |
| SpotBroker | 174 | $6.20 | 60 | 62.1 | 0.0 | $+248.92 | $+764.30 | 0.792 | 0/17 | Cut quantity from 70→60 to reduce overstock risk and holding... |

### Round 8 | 真实需求 196 | 观测需求 187 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 165 | $6.00 | 70 | 70.0 | 2.3 | $+133.72 | $+841.31 | 0.742 | 0/0 | Raised price from $5.8 to $5.9 to capture margin (R7 showed ... |
| PremiumCloud | 187 | $6.80 | 40 | 40.0 | 13.7 | $+99.51 | $+895.04 | 0.727 | 0/0 | Increased quantity by 5 (40→45) to improve stock coverage an... |
| SpotBroker | 168 | $6.20 | 60 | 60.0 | 10.0 | $+114.17 | $+878.46 | 0.767 | 0/0 | Raised quantity from 60 to 65 to restore scale efficiency an... |

### Round 9 | 真实需求 200 | 观测需求 198 | 市场均价 $6.40

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 176 | $6.00 | 80 | 78.8 | 0.0 | $+144.37 | $+985.68 | 0.807 | 0/1 | Raised quantity from 70→80 to better match observed demand s... |
| PremiumCloud | 188 | $6.80 | 40 | 41.2 | 15.5 | $+97.35 | $+992.40 | 0.706 | 1/0 | Increased quantity by 5 (40→45) to improve stock coverage an... |
| SpotBroker | 162 | $6.40 | 60 | 60.0 | 4.5 | $+133.36 | $+1011.82 | 0.756 | 0/0 | Raised price from 6.2 to 6.4 (legal max) to boost margin aft... |

### Round 10 | 真实需求 198 | 观测需求 198 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 152 | $6.00 | 60 | 70.9 | 8.0 | $+105.33 | $+1091.02 | 0.783 | 11/0 | Reduced quantity from 80 to 79 to prevent shortage and match... |
| PremiumCloud | 190 | $6.80 | 60 | 51.3 | 0.0 | $+170.97 | $+1163.37 | 0.779 | 0/9 | Increased quantity from 40 to 60 to close the fulfillment ga... |
| SpotBroker | 194 | $6.20 | 70 | 67.8 | 0.0 | $+143.46 | $+1155.28 | 0.817 | 0/2 | Raised quantity from 60 to 70 to address persistent shortage... |

### Round 11 | 真实需求 186 | 观测需求 183 | 市场均价 $6.27

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 152 | $6.00 | 80 | 66.6 | 0.0 | $+61.71 | $+1152.72 | 0.774 | 0/0 | Reduced quantity from 60→75 to better match demand signal (o... |
| PremiumCloud | 180 | $6.60 | 60 | 56.0 | 0.0 | $+128.96 | $+1292.33 | 0.772 | 0/0 | Raised quantity from 60 to 57 to align with actual allocated... |
| SpotBroker | 189 | $6.20 | 80 | 63.4 | 0.0 | $+51.79 | $+1207.06 | 0.800 | 0/0 | Raised quantity from 70 to 75 to reduce shortage risk after ... |

### Round 12 | 真实需求 176 | 观测需求 178 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 157 | $6.00 | 50 | 66.1 | 0.0 | $+168.46 | $+1321.18 | 0.768 | 6/0 | Reduced quantity from 80 to 70 to align with smoothed realiz... |
| PremiumCloud | 166 | $6.60 | 70 | 55.6 | 0.0 | $+78.41 | $+1370.74 | 0.766 | 0/0 | Reduced quantity from 60 to 56 to match recent realized dema... |
| SpotBroker | 177 | $6.40 | 60 | 54.2 | 0.0 | $+141.28 | $+1348.34 | 0.808 | 0/6 | Cut quantity by 20 (80→60) to fix overstocking; raised price... |

### Round 13 | 真实需求 172 | 观测需求 181 | 市场均价 $6.33

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 160 | $6.00 | 50 | 64.3 | 0.0 | $+99.21 | $+1420.39 | 0.764 | 14/0 | Raised quantity from 50 (R12) to 70 to restore buffer agains... |
| PremiumCloud | 169 | $6.60 | 70 | 54.1 | 0.0 | $+167.65 | $+1538.39 | 0.792 | 0/14 | Raised price by 0.2 (6.6→6.8) to offset negative price_bias ... |
| SpotBroker | 165 | $6.40 | 60 | 53.6 | 0.0 | $+95.82 | $+1444.16 | 0.794 | 0/0 | Reduced quantity from 60 to 55 to correct over-allocation tr... |

### Round 14 | 真实需求 190 | 观测需求 196 | 市场均价 $6.20

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 156 | $6.00 | 50 | 64.4 | 0.0 | $+104.61 | $+1524.99 | 0.760 | 14/0 | Raised quantity from 50 to 70 to test demand elasticity and ... |
| PremiumCloud | 153 | $6.40 | 60 | 64.6 | 0.0 | $+191.16 | $+1729.54 | 0.803 | 0/3 | Reduced quantity from 70 to 65 to match falling realized dem... |
| SpotBroker | 165 | $6.20 | 60 | 61.0 | 0.0 | $+209.44 | $+1653.60 | 0.845 | 0/12 | Raised quantity from 60 to 70 to improve realized sales capt... |

### Round 15 | 真实需求 197 | 观测需求 193 | 市场均价 $6.07

| Agent | 预测 | 定价 | 进货 | 销售 | 短缺 | 利润 | 累计利润 | 声誉 | 转移进/出 | 策略调整 |
|---|---|---|---|---|---|---|---|---|---|---|
| Hyperscaler | 167 | $6.00 | 40 | 40.7 | 17.8 | $+74.21 | $+1599.21 | 0.727 | 1/0 | Increased quantity from 50 to 60 to test demand elasticity a... |
| PremiumCloud | 137 | $6.00 | 60 | 64.2 | 15.0 | $+122.46 | $+1852.00 | 0.771 | 0/0 | Raised price from $6.4 to $6.5 to lift unit margin; held qua... |
| SpotBroker | 165 | $6.20 | 60 | 59.3 | 0.0 | $+127.43 | $+1781.03 | 0.884 | 0/1 | Raised quantity from 60 to 70 to better match realized deman... |

## 四、利润演变

| Round | Hyp | Pre | Spo | 市场均价 |
|---|---|---|---|---|
| 0 | $+124.32 | $-111.48 | $+69.85 | $5.47 |
| 1 | $-88.52 | $-136.24 | $+56.07 | $5.73 |
| 2 | $+134.62 | $+202.77 | $+25.84 | $5.87 |
| 3 | $+102.55 | $+240.87 | $+138.66 | $6.00 |
| 4 | $+58.03 | $+149.07 | $+99.50 | $6.20 |
| 5 | $+18.55 | $+149.43 | $+62.15 | $6.13 |
| 6 | $+201.22 | $+146.85 | $+63.30 | $6.20 |
| 7 | $+156.83 | $+154.26 | $+248.92 | $6.27 |
| 8 | $+133.72 | $+99.51 | $+114.17 | $6.33 |
| 9 | $+144.37 | $+97.35 | $+133.36 | $6.40 |
| 10 | $+105.33 | $+170.97 | $+143.46 | $6.33 |
| 11 | $+61.71 | $+128.96 | $+51.79 | $6.27 |
| 12 | $+168.46 | $+78.41 | $+141.28 | $6.33 |
| 13 | $+99.21 | $+167.65 | $+95.82 | $6.33 |
| 14 | $+104.61 | $+191.16 | $+209.44 | $6.20 |
| 15 | $+74.21 | $+122.46 | $+127.43 | $6.07 |

### 累计利润演变

| Round | Hyp | Pre | Spo |
|---|---|---|---|---|
| 0 | $+124.32 | $-111.48 | $+69.85 |
| 1 | $+35.80 | $-247.73 | $+125.92 |
| 2 | $+170.42 | $-44.96 | $+151.76 |
| 3 | $+272.97 | $+195.92 | $+290.42 |
| 4 | $+331.00 | $+344.98 | $+389.92 |
| 5 | $+349.54 | $+494.42 | $+452.07 |
| 6 | $+550.76 | $+641.27 | $+515.38 |
| 7 | $+707.60 | $+795.53 | $+764.30 |
| 8 | $+841.31 | $+895.04 | $+878.46 |
| 9 | $+985.68 | $+992.40 | $+1011.82 |
| 10 | $+1091.02 | $+1163.37 | $+1155.28 |
| 11 | $+1152.72 | $+1292.33 | $+1207.06 |
| 12 | $+1321.18 | $+1370.74 | $+1348.34 |
| 13 | $+1420.39 | $+1538.39 | $+1444.16 |
| 14 | $+1524.99 | $+1729.54 | $+1653.60 |
| 15 | $+1599.21 | $+1852.00 | $+1781.03 |

## 五、策略调整关键词分析

### Hyperscaler
**realized** (11), **observed** (10), **margin** (8), **better** (8), **match** (8), **profit** (7), **recent** (7), **while** (6), **capture** (5), **avoid** (5)

### PremiumCloud
**observed** (10), **margin** (8), **realized** (8), **bias** (8), **avoid** (7), **premium** (6), **inventory** (6), **eliminate** (6), **fairness** (6), **legal** (5)

### SpotBroker
**margin** (12), **realized** (7), **improve** (6), **trend** (6), **risk** (5), **shortage** (5), **bias** (5), **legal** (5), **observed** (4), **market** (4)

## 六、策略分化度

| 维度 | 观察 |
|---|---|
| **定价分化** | 最高均价 $6.66 (PremiumCloud) vs 最低 $5.78 (Hyperscaler)，价差 $0.89 |
| **产能分化** | 总进货量: Hyperscaler=1100 / PremiumCloud=870 / SpotBroker=1050 |
| **利润路径** | Hyperscaler=$+1599.21 / PremiumCloud=$+1852.00 / SpotBroker=$+1781.03 |
| **声誉分化** | Hyperscaler=0.727 / PremiumCloud=0.771 / SpotBroker=0.884 |

## 七、结论

- **赢家**: PremiumCloud，累计利润 $+1852.00
- **末位**: Hyperscaler，累计利润 $+1599.21
- **定价策略分化**: 价差 $0.89，说明角色设定得到有效维持
- **盈利稳定性**: 三 Agent 平均胜率 93.8%
