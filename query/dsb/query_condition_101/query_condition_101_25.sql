
i_category IN ('Children', 'Electronics', 'Men')
ca_state in ('AL', 'IA', 'ME', 'TX', 'WV')
d1.d_year = 1998
hd_income_band_sk BETWEEN 1 AND 7 AND hd_buy_potential = '>10000'
ss_sales_price / ss_list_price BETWEEN 38 * 0.01 AND 58 * 0.01

;


