# generators/generate_manual.py
import os
from datetime import datetime
from pathlib import Path

# ==================== CONTEÚDO DO MANUAL DE UTILIZAÇÃO ====================

MANUAL_UTILIZACAO = """# Manual de Utilização - DPMaster Pro v5.0

**Sistema de Gestão de Departamento Pessoal para Pequenas Empresas**

**Empresa:** PrimeTI Ltda | CNPJ: 62.938.903/0001-75 | Belo Horizonte - MG  
**Versão:** 5.0 — Small Business Edition  
**Data de Geração:** {data_atual}

## 1. Visão Geral

O **DPMaster Pro** é um sistema completo para gestão de Departamento Pessoal, desenvolvido especialmente para empresas com até 10 funcionários.

### Principais Funcionalidades (v5.0)

- **Dashboard 2.0**: Métricas, Gráficos de Custos e Centro de Notificações.
- **Centro de Notificações**: Alertas automáticos de aniversários, fim de experiência e férias.
- **Configurações da Empresa**: Suporte a diferentes regimes tributários (Simples Nacional, etc).
- **Assistente de Admissão**: Guia passo a passo para novas contratações.
- **Gestão Documental**: Arquivamento de documentos digitalizados dos funcionários.
- **Folha de Pagamento**: Cálculos automáticos com visibilidade de FGTS e encargos patronais.
- **Relatórios Avançados**: PDFs gerenciais e folha analítica.

## 2. Perfis de Acesso

| Perfil       | Permissões                                                                 |
|--------------|----------------------------------------------------------------------------|
| **admin**    | Acesso total (Usuários, Configurações da Empresa, Logs)                    |
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
Última atualização: {data_atual}
"""

# ==================== FUNÇÃO PRINCIPAL ====================

def gerar_manuais():
    """Gera/atualiza todos os manuais automaticamente"""
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    
    # Criar pasta docs se não existir
    Path("docs").mkdir(exist_ok=True)
    
    # 1. Manual de Utilização (para usuários)
    conteudo_utilizacao = MANUAL_UTILIZACAO.format(data_atual=data_atual)
    
    with open("docs/manual_utilizacao.md", "w", encoding="utf-8") as f:
        f.write(conteudo_utilizacao)
    
    print("✅ Manual de Utilização gerado com sucesso: docs/manual_utilizacao.md")
    
    # 2. Criar versão PDF (chama a função já existente no sistema)
    try:
        # Importar do app principal (vamos ajustar depois)
        from app import gerar_manual_sistema_pdf  # será ajustado
        
        buffer = gerar_manual_sistema_pdf()
        if buffer:
            with open("docs/manual_utilizacao.pdf", "wb") as f:
                f.write(buffer.getvalue())
            print("✅ Manual em PDF gerado: docs/manual_utilizacao.pdf")
    except Exception as e:
        print(f"⚠️ Não foi possível gerar PDF automaticamente: {e}")
        print("   → Use o botão dentro do sistema para gerar o PDF completo.")

    # 3. Atualizar changelog básico
    with open("docs/changelog.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d')} - Atualização\n")
        f.write("- Documentação atualizada automaticamente via script\n")
    
    print("\n🎉 **Documentação atualizada com sucesso!**")


if __name__ == "__main__":
    gerar_manuais()