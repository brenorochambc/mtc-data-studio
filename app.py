import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="MTC Data Studio - Permanente", page_icon="🛠️", layout="wide")

# Estilo Customizado
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #2a9d8f;
        color: white;
    }
    .stButton>button {
        background-color: #264653;
        color: white;
        font-weight: bold;
        width: 100%;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_column_name(name):
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

# Título e Descrição
st.title("🛠️ MTC Data Studio")
st.subheader("Sistema Universal de Limpeza e Engenharia de Dados")
st.markdown("Suba qualquer CSV de pipeline e personalize quais colunas e tags você deseja transformar em métricas.")

# 1. Upload do Arquivo
uploaded_file = st.file_uploader("Arraste seu CSV bruto aqui", type="csv")

if uploaded_file is not None:
    try:
        # Carregamento inicial para análise
        @st.cache_data
        def load_raw_data(file):
            return pd.read_csv(file)

        df_raw = load_raw_data(uploaded_file)
        initial_cols = df_raw.columns.tolist()
        
        st.divider()
        
        # Layout de Colunas para Configuração
        col_config, col_preview = st.columns([1, 2])
        
        with col_config:
            st.header("⚙️ Configurações")
            
            # Seleção de Colunas Originais
            st.subheader("1. Colunas do CSV")
            selected_cols = st.multiselect(
                "Quais colunas você deseja manter?",
                options=initial_cols,
                default=[c for c in initial_cols if c.lower() in ['contact name', 'phone', 'email', 'stage', 'status', 'status etapa', 'opportunity id', 'tags', 'updated on']]
            )
            
            # Seleção de Tags para Explosão
            st.subheader("2. Explosão de Tags")
            if any(c.lower() == 'tags' for c in selected_cols):
                tag_col = next((c for c in selected_cols if c.lower() == 'tags'), None)
                
                if tag_col:
                    all_tags = []
                    df_raw[tag_col].dropna().apply(lambda x: all_tags.extend([t.strip().lower() for t in str(x).split(',') if t.strip()]))
                    unique_tags = sorted(list(set(all_tags)))
                    
                    selected_tags = st.multiselect(
                        "Quais tags devem virar colunas individuais?",
                        options=unique_tags,
                        help="Cada tag selecionada criará uma nova coluna com 0 ou 1."
                    )
                else:
                    selected_tags = []
            else:
                st.warning("Selecione a coluna 'tags' acima para habilitar a explosão.")
                selected_tags = []

            # Opções de Limpeza
            st.subheader("3. Regras de Limpeza")
            do_dedup = st.checkbox("Remover duplicatas (pelo Opportunity ID)", value=True)
            do_snake_case = st.checkbox("Converter nomes para snake_case", value=True)

        with col_preview:
            st.header("📊 Prévia do Resultado")
            
            # PROCESSAMENTO
            df_proc = df_raw[selected_cols].copy()
            
            if do_snake_case:
                df_proc.columns = [clean_column_name(c) for c in df_proc.columns]
            
            if do_dedup:
                id_col = next((c for c in df_proc.columns if 'opportunity_id' in c or 'id' in c.lower()), None)
                update_col = next((c for c in df_proc.columns if 'updated' in c.lower()), None)
                if id_col:
                    if update_col:
                        df_proc = df_proc.sort_values(update_col, ascending=False)
                    df_proc = df_proc.drop_duplicates(subset=[id_col], keep='first')
            
            if selected_tags:
                tag_col_proc = next((c for c in df_proc.columns if 'tags' in c.lower()), None)
                if tag_col_proc:
                    for tag in selected_tags:
                        col_name = f"tag_{clean_column_name(tag)}"
                        df_proc[col_name] = df_proc[tag_col_proc].fillna('').astype(str).str.lower().apply(
                            lambda x: 1 if tag in [t.strip() for t in x.split(',')] else 0
                        )
            
            st.dataframe(df_proc.head(20), use_container_width=True)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Linhas Finais", len(df_proc))
            m2.metric("Colunas Totais", len(df_proc.columns))
            m3.metric("Tags Explodidas", len(selected_tags))
            
            st.divider()
            csv = df_proc.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 BAIXAR CSV PERSONALIZADO",
                data=csv,
                file_name=f"mtc_studio_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("👋 Bem-vindo! Suba um arquivo CSV para começar a configurar sua limpeza de dados.")
