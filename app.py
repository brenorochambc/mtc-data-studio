import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="MTC Data Studio - Elite", page_icon="🛠️", layout="wide")

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

def format_phone(val):
    if pd.isna(val):
        return ""
    # Converte para string e remove o .0 se existir
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    # Remove qualquer caractere que não seja número
    s = re.sub(r'\D', '', s)
    return s

# Título e Descrição
st.title("🛠️ MTC Data Studio - Versão Elite")
st.subheader("Sistema Universal de Limpeza e Engenharia de Dados")
st.markdown("Personalize colunas, defina tipos de dados e exploda tags para métricas fidedignas.")

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
            st.subheader("1. Seleção de Colunas")
            selected_cols = st.multiselect(
                "Quais colunas você deseja manter?",
                options=initial_cols,
                default=[c for c in initial_cols if c.lower() in ['contact name', 'phone', 'email', 'stage', 'status', 'status etapa', 'opportunity id', 'tags', 'updated on', 'created on']]
            )
            
            # Mapeamento de Tipos (Sua Sugestão!)
            st.subheader("2. Mapeamento de Tipos")
            col_types = {}
            if selected_cols:
                for col in selected_cols:
                    # Sugestão automática baseada no nome
                    default_type = "Texto"
                    if any(word in col.lower() for word in ['date', 'on', 'at', 'criado', 'atualizado']):
                        default_type = "Data"
                    elif any(word in col.lower() for word in ['phone', 'telefone', 'celular', 'whatsapp']):
                        default_type = "Telefone"
                    
                    col_types[col] = st.selectbox(
                        f"Tipo para: {col}",
                        options=["Texto", "Data", "Telefone", "Número"],
                        index=["Texto", "Data", "Telefone", "Número"].index(default_type),
                        key=f"type_{col}"
                    )

            # Seleção de Tags para Explosão
            st.subheader("3. Explosão de Tags")
            tag_col = next((c for c in selected_cols if c.lower() == 'tags'), None)
            if tag_col:
                all_tags = []
                df_raw[tag_col].dropna().apply(lambda x: all_tags.extend([t.strip().lower() for t in str(x).split(',') if t.strip()]))
                unique_tags = sorted(list(set(all_tags)))
                
                selected_tags = st.multiselect(
                    "Quais tags devem virar colunas?",
                    options=unique_tags
                )
            else:
                st.warning("Selecione a coluna 'tags' para explodir.")
                selected_tags = []

            # Opções de Limpeza
            st.subheader("4. Regras de Limpeza")
            do_dedup = st.checkbox("Remover duplicatas (pelo Opportunity ID)", value=True)
            do_snake_case = st.checkbox("Converter nomes para snake_case", value=True)

        with col_preview:
            st.header("📊 Prévia do Resultado")
            
            # PROCESSAMENTO
            df_proc = df_raw[selected_cols].copy()
            
            # Aplicar Tipagem Manual
            for col, t in col_types.items():
                if t == "Data":
                    df_proc[col] = pd.to_datetime(df_proc[col], errors='coerce').dt.strftime('%Y-%m-%d')
                elif t == "Telefone":
                    df_proc[col] = df_proc[col].apply(format_phone)
                elif t == "Número":
                    df_proc[col] = pd.to_numeric(df_proc[col], errors='coerce')
                else:
                    df_proc[col] = df_proc[col].fillna('').astype(str).str.strip()

            # Padronização de Nomes de Colunas
            if do_snake_case:
                df_proc.columns = [clean_column_name(c) for c in df_proc.columns]
            
            # Deduplicação
            if do_dedup:
                id_col = next((c for c in df_proc.columns if 'opportunity_id' in c or 'id' in c.lower()), None)
                update_col = next((c for c in df_proc.columns if 'updated' in c or 'atualizado' in c), None)
                if id_col:
                    if update_col:
                        temp_date = pd.to_datetime(df_proc[update_col], errors='coerce')
                        df_proc = df_proc.iloc[temp_date.argsort()[::-1]]
                    df_proc = df_proc.drop_duplicates(subset=[id_col], keep='first')
            
            # Explosão de Tags
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
    st.info("👋 Bem-vindo! Suba um arquivo CSV para começar.")
