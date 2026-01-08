# 📊 Sistema de Conciliação Contábil

Sistema multi-empresa para conciliação bancária e geração de lançamentos contábeis em CSV.

## 🏢 Empresas Suportadas

### 💊 Drogarias
- Upload de extrato bancário (.xlsx)
- Upload de planilha de lançamentos
- Conciliação automática por data e valor
- Tratamento de multas, juros, descontos e tarifas

### 🏭 Tradição Comércio e Serviços
- Suporte a múltiplos bancos (SICOOB e Banco do Brasil)
- Upload de extratos em PDF ou Excel
- Planilha de movimentação com múltiplas abas (PAG SICOOB, PAG BB, CAIXA EMPRESA)
- Sistema de classificação de contas contábeis por histórico

## 📁 Estrutura de Pastas

```
Drogarias-main/
├── streamlit_conciliacao/
│   ├── app.py                    # Aplicação principal Streamlit
│   ├── conciliador.py            # Lógica de conciliação Drogarias
│   ├── cadastro.py               # CRUD de contas
│   ├── utils.py                  # Utilitários gerais
│   ├── page_tradicao.py          # Página Streamlit para Tradição
│   └── tradicao/                 # Módulo Tradição
│       ├── conciliador_tradicao.py
│       ├── utils_tradicao.py
│       └── extrator_pdf.py
├── data/
│   └── {CNPJ}/contas_config.json # Configurações por empresa (Drogarias)
├── logs/
├── tests/
├── requirements.txt
└── setup.py
```

## 🚀 Instalação

```bash
# Clonar repositório
git clone https://github.com/Gms006/Drogarias.git
cd Drogarias

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

## ▶️ Execução

```bash
streamlit run streamlit_conciliacao/app.py
```

## 📋 Formato do CSV de Saída

O sistema gera um CSV padronizado com as seguintes colunas:

| Coluna | Descrição |
|--------|-----------|
| Data | Data do lançamento (DD/MM/AAAA) |
| Cod Conta Débito | Código da conta debitada |
| Cod Conta Crédito | Código da conta creditada |
| Valor | Valor do lançamento (formato 1234,56) |
| Cod Histórico | Código do histórico contábil |
| Complemento | Descrição complementar (NF + Fornecedor) |
| Inicia Lote | Marcador de início de lote (1 ou vazio) |

### Códigos de Histórico (Tradição)
- **34**: Pagamentos via conta bancária
- **1**: Pagamentos via caixa
- **11**: Tarifas bancárias e seguros
- **2**: Recebimentos bancários
- **9**: Depósitos

### Contas Bancárias (Tradição)
- **SICOOB**: Conta 543
- **Banco do Brasil**: Conta 495
- **Caixa**: Conta 5

## 📊 Regras de Contabilização (Tradição)

### Pagamentos
```
Débito: Conta do fornecedor (busca na planilha FINANCEIRO)
Crédito: Conta do banco (543 SICOOB / 495 BB / 5 Caixa)
```

### Entradas/Depósitos
```
Débito: Conta do banco
Crédito: Conta do cliente/origem
```

### Tarifas (Conta 170)
As tarifas preservam a classificação do banco, buscando primeiro na aba do respectivo banco.

## 📁 Arquivos Necessários (Tradição)

### 1. Planilha de Contas Contábeis
- **Aba FINANCEIRO**: Nome do fornecedor → Conta contábil
- **Aba BANCO DO BRASIL**: Saídas e Entradas com históricos → Contas
- **Aba SICOOB**: Saídas e Entradas com históricos → Contas

### 2. Planilha de Movimentação
- **Aba PAG SICOOB**: DATA, PAGAMENTO, VALOR, NF, DATA NF, OBS
- **Aba PAG BB**: DATA, PAGAMENTO, VALOR, NF, DATA NF, OBS
- **Aba CAIXA EMPRESA**: Saídas e Entradas do caixa físico

### 3. Extratos Bancários
- Formato Excel (.xlsx) com colunas: Data, Documento, Historico, Credito, Debito, Saldo
- Ou PDF dos bancos (requer pdfplumber)

## ⚠️ Tratamento de Erros

O sistema bloqueia a geração do CSV quando encontra lançamentos não classificados, exibindo:
- Lista de lançamentos não encontrados
- Download de CSV com os itens pendentes
- Instruções para cadastrar as contas

## 🔧 Dependências

- streamlit >= 1.28.0
- pandas >= 2.0.0
- openpyxl >= 3.1.0
- pdfplumber >= 0.10.0 (opcional, para PDFs)
- numpy >= 1.24.0

## 📝 Licença

Uso interno - Automação Contábil

---
**v2.0** - Dezembro/2025
