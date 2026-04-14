# VN30 Clustered Portfolio Optimization

Kho ma nguon cong khai phuc vu tai lap nghien cuu ve xay dung va toi uu hoa danh muc co phieu VN30 bang cach ket hop phan cum va mo hinh Markowitz.

## Noi dung repo

- `notebooks/`: chuoi notebook chinh tu thu thap du lieu den backtest
- `notebooks/helpers/`: cac helper module duoc notebook su dung truc tiep
- `data/raw/`: du lieu dau vao
- `data/processed/`: du lieu da xu ly va cac artifact trung gian
- `reports/eda/`: artifact EDA
- `reports/preprocess/`: artifact tien xu ly
- `reports/corr_cluster/`: artifact phan cum
- `reports/cluster_insight/`: artifact dien giai cum
- `reports/backtest_static/`: artifact backtest tinh trong mau
- `reports/backtest_rolling/`: artifact backtest rolling ngoai mau
- `tests/`: test cho helper va notebook contract

## Khong dua vao repo public nay

- `memory-bank/`
- `docs/superpowers/`
- `reports/report_draft/`
- cac file tong hop va workflow noi bo

## Cai dat

Yeu cau:

- Python `>=3.11,<3.12`
- `uv` hoac mot trinh quan ly moi truong tuong duong

Thiet lap nhanh voi `uv`:

```bash
uv sync --extra dev
```

## Thu tu notebook

1. `00_download_data.ipynb`
2. `01_eda.ipynb`
3. `02_preprocess.ipynb`
4. `03_returns_and_validation.ipynb`
5. `04_corr_cluster.ipynb`
6. `05_cluster_insight.ipynb`
7. `06_markowitz_static.ipynb`
8. `07_backtest_static_portfolio.ipynb`
9. `08_backtest_rolling_markowitz.ipynb`

## Chay test

```bash
uv run pytest -q -p no:cacheprovider
```
