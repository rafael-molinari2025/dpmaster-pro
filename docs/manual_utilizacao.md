# Manual de Utilização - DPMaster Pro v4.0

**Sistema de Gestão de Departamento Pessoal**

**Empresa:** PrimeTI Ltda | CNPJ: 62.938.903/0001-75 | Belo Horizonte - MG  
**Versão:** 4.0  
**Data de Geração:** 25/04/2026 às 23:34:52

## 1. Visão Geral

O **DPMaster Pro** é um sistema completo para gestão de Departamento Pessoal, desenvolvido em Python + Streamlit.

### Principais Funcionalidades

- Dashboard com métricas em tempo real
- Cadastro completo de funcionários + gestão documental
- Folha de Pagamento com cálculo automático (INSS, IRRF, VT)
- 13º Salário (1ª e 2ª parcelas)
- Cálculo de Férias com abono e 13º nas férias
- Rescisão contratual com verbas rescisórias
- Integração com eSocial (geração de XMLs + fila de transmissão)
- Relatórios e PDFs gerenciais
- Sistema de logs e auditoria

## 2. Perfis de Acesso

| Perfil       | Permissões                                                                 |
|--------------|----------------------------------------------------------------------------|
| **admin**    | Acesso total (inclui usuários e logs)                                      |
| **coordenador** | Dashboard, Cadastros, Folha, 13º, Férias, Rescisão, eSocial, Relatórios |
| **funcionario** | Apenas visualização (Dashboard e Relatórios)                             |

**Credenciais padrão (alterar imediatamente):**
- `admin / 123456`
- `coordenador / 123456`
- `funcionario / 123456`

## 3. Como Usar os Módulos Principais

### 3.1 Dashboard
Tela inicial com métricas: funcionários ativos, total da folha, média salarial e eventos eSocial pendentes.

### 3.2 Cadastro de Funcionários
- **Aba Dados Cadastrais**: Nome, CPF, RG, admissão, salário, dependentes, benefícios...
- **Aba Documentos**: Upload de RG, CPF, CTPS, contratos, atestados (PDF/JPG/PNG até 10MB).

### 3.3 Folha de Pagamento
1. Escolha o mês
2. Clique em "Calcular Todos" para um cálculo padrão baseado no salário base e tabelas vigentes.
3. Para **ajustes manuais**, abra o expander do funcionário e use a seção "Itens Extras".
   - Adicione proventos (bônus, prêmios) ou descontos (faltas, convênios extras).
   - O sistema recalcula o líquido automaticamente.
4. Gere o **Contracheque PDF**, que exibirá todos os itens detalhadamente.

### 3.4 13º Salário
- Adiantamento (1ª parcela) → sem descontos
- Final (2ª parcela) → com INSS e IRRF + cálculo de avos

### 3.5 Férias
Cálculo completo com:
- Férias base + 1/3 constitucional
- Abono pecuniário (opcional)
- 13º nas férias (opcional)
- Gera automaticamente evento S-2230 no eSocial

### 3.6 Rescisão
Suporta todos os tipos de desligamento (sem justa causa, acordo, justa causa, etc.) com cálculo automático de:
- Saldo de salário
- Férias proporcionais + 1/3
- 13º proporcional
- Aviso prévio
- Multa FGTS (40% ou 20%)

### 3.7 eSocial — Painel de Transmissão
- Fila de eventos com status (Pendente → Transmitido)
- Geração de XMLs (S-1200, S-2200, S-2230, S-2299)
- Simulação de transmissão

### 3.8 Relatórios
Vários formatos disponíveis (PDF e tabelas interativas):
- Folha Analítica
- Ficha de Cadastro
- Ficha Financeira Anual
- Resumo Geral da Folha
- Memória de Cálculo

### 3.9 Importação de Dados
Módulo para carga massiva de informações via arquivos CSV.
- **Importar Funcionários**: Use para cadastrar novos funcionários em lote. Baixe o modelo CSV para garantir que as colunas estejam corretas.
- **Importar Itens de Folha**: Use para lançar proventos e descontos para múltiplos funcionários de uma vez (ex: prêmios do mês, faltas da unidade).
- **Validação**: O sistema valida CPFs existentes para evitar duplicidade.

## 4. Regras de Cálculo (2026)

**INSS (Progressivo):**
- Até R$ 1.518,00 → 7,5%
- Até R$ 2.793,88 → 9,0%
- Até R$ 4.190,83 → 12,0%
- Até R$ 8.157,41 → 14,0%

**IRRF:**
- Até R$ 2.259,20 → Isento
- Dedução por dependente: R$ 189,59

**Vale-Transporte:** limitado a 6% do salário base

## 5. Auditoria e Segurança

Para garantir a credibilidade e integridade dos processos, o **DPMaster Pro** mantém um registro de auditoria imutável.
- **Logs do Sistema**: Todos os cálculos e alterações críticas são registrados com timestamp e usuário responsável.
- **Imutabilidade**: Não é permitido apagar ou limpar os logs através da interface do sistema.
- **Configurações de Tabelas**: O sistema permite a atualização anual das tabelas de INSS e IRRF pelo Administrador, garantindo que o software permaneça atualizado com a legislação vigente sem necessidade de suporte técnico.

---

**Manual gerado automaticamente** — Não edite diretamente este arquivo.
Última atualização: 25/04/2026 às 23:34:52
