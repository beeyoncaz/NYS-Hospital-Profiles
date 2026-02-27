import pandas as pd

cols_to_keep = ['PRVDR_CTGRY_SBTYP_CD', 'PRVDR_CTGRY_CD', 'CHOW_DT', 'ELGBLTY_SW', 'MDCD_VNDR_NUM', 'PRVDR_NUM', 'GNRL_CNTL_TYPE_CD', 'CBSA_URBN_RRL_IND', 'CBSA_CD', 'ACRDTN_TYPE_CD', 'TOT_AFLTD_AMBLNC_SRVC_CNT', 'TOT_AFLTD_HHA_CNT', 'CRTFD_BED_CNT', 'BED_CNT', 'MDCL_SCHL_AFLTN_CD', 'PGM_PRTCPTN_CD', 'LPN_LVN_CNT', 'RSDNT_PHYSN_CNT', 'RN_CNT']

df = pd.read_csv('data/Hospital_and_other.DATA.Q4_2025.csv')
df_filtered = df[df['PRVDR_CTGRY_SBTYP_CD']==1]
df_filtered = df_filtered[cols_to_keep]
df_filtered.to_csv('collected-data/hospitals_filtered.csv', index=False)


