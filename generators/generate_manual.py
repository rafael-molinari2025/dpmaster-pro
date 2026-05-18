# generators/generate_manual.py
from datetime import datetime
from pathlib import Path

# ==================== CONTEÚDO DO MANUAL DE UTILIZAÇÃO ====================

MANUAL_UTILIZACAO = """# Manual de Utilização — DPMaster Pro v5.0

**Sistema de Gestão de Departamento Pessoal para Pequenas Empresas**

**Versão:** 5.0 — Small Business Edition | **Atualização:** {data_atual}

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Primeiros Passos — Acesso ao Sistema](#primeiros-passos)
3. [Gestão de Empresas](#gestão-de-empresas) *(Novidade v5.0)*
4. [Dashboard](#dashboard)
5. [Gerenciar Usuários](#gerenciar-usuários)
6. [Cadastro de Funcionários](#cadastro-de-funcionários)
7. [Folha de Pagamento](#folha-de-pagamento)
8. [Gestão de Ponto](#gestão-de-ponto)
9. [13º Salário](#13º-salário)
10. [Férias](#férias)
11. [Rescisão Contratual](#rescisão-contratual)
12. [eSocial — Painel de Transmissão](#esocial)
13. [Relatórios e PDFs](#relatórios-e-pdfs)
14. [Importação de Dados](#importação-de-dados)
15. [Configuração de Tabelas INSS/IRRF](#configuração-de-tabelas)
16. [Configurações da Empresa](#configurações-da-empresa)
17. [Backup e Restauração](#backup-e-restauração)
18. [Logs do Sistema](#logs-do-sistema)
19. [Regras de Cálculo Vigentes (2026)](#regras-de-cálculo)
20. [Segurança e Boas Práticas](#segurança-e-boas-práticas)
21. [Perguntas Frequentes](#perguntas-frequentes)

---

## 1. Visão Geral

O **DPMaster Pro** é um sistema web completo de Departamento Pessoal, desenvolvido especialmente para escritórios contábeis e pequenas empresas que precisam gerenciar múltiplos CNPJs em um único ambiente seguro.

### O que o sistema faz

- Gerencia funcionários de **múltiplas empresas** com isolamento total de dados
- Calcula **folha de pagamento**, **13º salário**, **férias** e **rescisão** automaticamente
- Gera **PDFs profissionais** de todos os documentos trabalhistas
- Controla **ponto eletrônico** simplificado com horas extras e faltas
- Gera **XMLs do eSocial** (S-1200, S-2200, S-2230, S-2299)
- Mantém **histórico de auditoria** completo de todas as ações
- Realiza **backup automático** dos dados antes de operações críticas

### Novidades da Versão 5.0

| Funcionalidade | Descrição |
|---|---|
| **Multi-empresa** | Cadastre várias empresas e gerencie cada uma de forma isolada |
| **Seletor de empresa no login** | Usuário acessa apenas os dados da empresa vinculada |
| **Admin Global** | Perfil especial sem restrição de empresa para contadores |
| **Dashboard avançado** | Gráficos de evolução de custos e distribuição por departamento |
| **Centro de notificações** | Alertas de aniversários, fim de experiência e férias a vencer |
| **Assistente de admissão** | Guia passo a passo com kit de documentos em ZIP |
| **Gestão documental** | Upload e organização de documentos por funcionário |

---

## 2. Primeiros Passos — Acesso ao Sistema

### 2.1 Tela de Login

Ao acessar o sistema, você verá a tela de login com três campos:

**Passo 1 — Selecionar a Empresa**
No campo **"Empresa"**, escolha no menu suspenso a empresa à qual seu usuário pertence. Apenas empresas ativas cadastradas pelo administrador aparecem nessa lista.

> **Importante:** Se você for um **Administrador Global**, pode selecionar qualquer empresa — seu acesso não fica restrito. Após o login, o sistema exibirá os dados da empresa que você selecionou.

**Passo 2 — Informar Usuário e Senha**
Digite seu nome de usuário (campo "Usuário") e sua senha no campo correspondente.

**Passo 3 — Entrar**
Clique no botão **"Entrar →"** para acessar o sistema.

### 2.2 Credenciais Padrão

Na primeira execução do sistema, os seguintes usuários são criados automaticamente:

| Usuário | Senha | Perfil | Empresa |
|---|---|---|---|
| `admin` | `123456` | Admin Global | Nenhuma (acesso total) |
| `coordenador` | `123456` | Coordenador | Empresa padrão (ID 1) |
| `funcionario` | `123456` | Funcionário | Empresa padrão (ID 1) |

> **⚠️ Atenção:** Altere as senhas padrão imediatamente após o primeiro acesso. O sistema exige senhas com no mínimo 8 caracteres.

### 2.3 Perfis de Acesso

O sistema possui três níveis de permissão hierárquicos:

| Perfil | O que pode fazer |
|---|---|
| **admin** | Acesso total: gerenciar empresas, usuários, tabelas, logs, backup e todas as operações |
| **coordenador** | Cadastros, folha, ponto, 13º, férias, rescisão, eSocial, importação e relatórios |
| **funcionario** | Somente visualização: dashboard e relatórios |

### 2.4 Bloqueio por Tentativas

Após **5 tentativas de login incorretas**, a conta fica bloqueada por **5 minutos**. O contador é reiniciado após um login bem-sucedido. Isso protege o sistema contra tentativas de acesso não autorizado.

### 2.5 Timeout de Sessão

A sessão expira automaticamente após **30 minutos de inatividade**. Ao expirar, o sistema redireciona para a tela de login preservando a segurança dos dados.

### 2.6 Alterar Senha

Na barra lateral, clique em **"🔑 Alterar Senha"** e preencha:
- Senha atual
- Nova senha (mínimo 8 caracteres)
- Confirmação da nova senha

Clique em **"Alterar"** para salvar. A senha é armazenada com hash SHA-256 e salt individual por usuário.

---

## 3. Gestão de Empresas *(Novidade v5.0)*

> **Acesso:** Somente perfil **admin**
> **Menu:** 🏢 Cadastro de Empresas

Esta funcionalidade permite que um escritório contábil ou grupo empresarial gerencie múltiplos CNPJs dentro do mesmo sistema, com **isolamento total de dados** entre elas.

### 3.1 Como Funciona o Multi-empresa

Cada empresa cadastrada possui seu próprio conjunto de:
- Funcionários e folhas de pagamento
- Histórico de eSocial
- Configurações tributárias (regime, alíquotas)

Usuários vinculados a uma empresa **não podem ver** dados de outras empresas. Apenas o **Admin Global** (usuário sem empresa vinculada) tem visão completa de todas as empresas.

### 3.2 Cadastrar Nova Empresa

1. No menu lateral, acesse **"🏢 Cadastro de Empresas"**
2. Clique no expander **"➕ Nova Empresa"**
3. Preencha os campos obrigatórios:
   - **Razão Social** *(obrigatório)*
   - **CNPJ** *(obrigatório — deve ser único no sistema)*
   - **Endereço**
   - **Regime Tributário**: Simples Nacional, Lucro Presumido ou Lucro Real
   - **INSS Patronal (%)**: alíquota do empregador (ex: 20% para Lucro Presumido/Real)
   - **RAT / FAP (%)**: risco ambiental do trabalho
   - **Terceiros (%)**: contribuição a terceiros (SESC, SENAC etc.)
4. Clique em **"💾 Cadastrar Empresa"**

> **Simples Nacional:** Empresas no Simples (exceto Anexo IV) geralmente colocam 0% no INSS Patronal, pois esse encargo já está incluído no DAS.

### 3.3 Editar Empresa

Na lista de empresas cadastradas, cada empresa aparece como um expander com ícone de status:
- 🟢 Empresa ativa
- 🔴 Empresa inativa

Clique sobre o nome da empresa para expandir, faça as alterações necessárias e clique em **"💾 Salvar Alterações"**.

Para **desativar** uma empresa sem excluí-la, desmarque a opção **"Empresa Ativa"** e salve. Empresas inativas não aparecem no seletor da tela de login.

### 3.4 Excluir Empresa

Clique em **"🗑️ Excluir"** dentro do expander da empresa. O sistema **não permite excluir** uma empresa que possua funcionários cadastrados. Primeiro transfira ou inative os funcionários, depois exclua a empresa.

> O sistema também exige ao menos **uma empresa ativa** — a última não pode ser excluída.

### 3.5 Vincular Usuário a uma Empresa

Ao criar ou editar um usuário em **"👥 Gerenciar Usuários"**, escolha a empresa no campo **"Empresa Vinculada"**. A opção **"Nenhuma (Admin Global)"** cria um administrador sem restrição de empresa.

### 3.6 Dados da Empresa nos Documentos

Todos os PDFs gerados (contracheques, rescisões, férias etc.) usam automaticamente o nome, CNPJ e endereço da empresa da sessão ativa, sem necessidade de configuração adicional.

---

## 4. Dashboard

> **Acesso:** Todos os perfis
> **Menu:** 🏠 Dashboard

O Dashboard é a tela inicial do sistema após o login. Exibe uma visão resumida da situação atual da empresa selecionada.

### 4.1 Métricas Principais

Na parte superior, cinco indicadores rápidos:

| Métrica | O que mostra |
|---|---|
| **Funcionários Ativos** | Total de colaboradores com situação "Ativo" |
| **Funcionários Inativos** | Total com situação diferente de "Ativo" |
| **Total Folha Base** | Soma dos salários base de todos os ativos |
| **Média Salarial** | Média dos salários base dos ativos |
| **eSocial Pendente** | Eventos na fila com status "Pendente" ou "Aguardando" |

### 4.2 Gráfico de Evolução de Custos

Mostra a evolução mês a mês do total líquido pago na folha de pagamento ao longo do ano corrente. Cada ponto representa um mês em que houve folha calculada.

> O gráfico só aparece se a biblioteca **Plotly** estiver instalada.

### 4.3 Distribuição por Departamento

Gráfico de pizza mostrando a proporção de funcionários ativos em cada departamento cadastrado.

### 4.4 Centro de Notificações

Alertas automáticos exibidos no dashboard:

- **🎂 Aniversários do Mês:** Funcionários que fazem aniversário no mês atual
- **⏰ Fim de Experiência (próximos 30 dias):** Colaboradores com contrato de experiência próximo do vencimento (considerando 90 dias de admissão)
- **🏖️ Férias Vencidas/a Vencer:** Funcionários com período aquisitivo de 12 meses completado ou prestes a completar

---

## 5. Gerenciar Usuários

> **Acesso:** Somente perfil **admin**
> **Menu:** 👥 Gerenciar Usuários

### 5.1 Cadastrar Novo Usuário

1. Clique no expander **"➕ Novo Usuário"**
2. Preencha os campos:
   - **Nome Completo**
   - **Usuário** (login — deve ser único no sistema)
   - **Senha** (mínimo 8 caracteres)
   - **Perfil**: admin, coordenador ou funcionario
   - **Empresa Vinculada**: selecione a empresa ou "Nenhuma (Admin Global)"
3. Clique em **"Cadastrar"**

### 5.2 Lista de Usuários

Cada usuário é exibido com nome, login, perfil e empresa vinculada. Para **excluir** um usuário, clique no ícone 🗑️ ao lado do seu nome.

> Não é possível excluir o próprio usuário com o qual você está logado.

### 5.3 Boas Práticas de Usuários

- Crie um usuário **coordenador** por empresa para o responsável pelo RH
- Use o perfil **funcionario** apenas para consulta de dados próprios
- Nunca compartilhe credenciais entre pessoas — cada pessoa deve ter seu próprio login
- Troque as senhas padrão `123456` imediatamente

---

## 6. Cadastro de Funcionários

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 👤 Cadastro de Funcionários

A tela de cadastro possui três abas: **Dados Cadastrais**, **Documentos** e **Assistente de Admissão**.

### 6.1 Aba — Dados Cadastrais

**Campos do formulário:**

| Campo | Obrigatório | Observação |
|---|---|---|
| Nome Completo | ✅ Sim | |
| CPF | ✅ Sim | Validado com algoritmo oficial dos dígitos verificadores |
| RG | Não | |
| Data de Nascimento | Não | |
| Data de Admissão | Não | Padrão: data de hoje |
| Cargo | Não | Aparece nos documentos gerados |
| Departamento | Não | Usado nos gráficos do Dashboard |
| Salário Base (R$) | Não | Base para todos os cálculos |
| Dependentes | Não | Quantidade — afeta o cálculo do IRRF |
| Tem Plano de Saúde? | Não | Marque para ativar o campo de valor |
| Valor Plano Saúde (R$) | Não | Descontado na folha se marcado |
| Valor VT Mensal (R$) | Não | Sujeito ao limite de 6% do salário |
| Situação | Não | Ativo / Inativo |

**Para cadastrar:** Preencha os campos e clique em **"💾 Salvar"**.

**Para editar:** Clique no botão ✏️ ao lado do nome do funcionário na lista. Os dados carregam no formulário. Faça as alterações e clique em **"💾 Atualizar"**.

**Para excluir:** Clique no ícone 🗑️. A exclusão remove o funcionário e todo o seu histórico de folha. Esta ação não pode ser desfeita — o sistema cria um backup automático antes.

> **CPF duplicado:** O sistema não permite cadastrar dois funcionários com o mesmo CPF na mesma empresa.

### 6.2 Aba — Documentos do Funcionário

Permite armazenar documentos digitalizados vinculados a cada funcionário.

**Tipos aceitos:** PDF, JPG, PNG (até 10 MB por arquivo)

**Como usar:**
1. Selecione o funcionário no campo "Selecione o Funcionário"
2. Escolha a categoria do documento (RG, CPF, CTPS, Contrato, Atestado, Outros)
3. Clique em "Browse files" e selecione o arquivo
4. Clique em **"📎 Fazer Upload"**

Os documentos ficam armazenados na pasta `data_dp/documentos/{id_funcionario}/` e podem ser visualizados e baixados a qualquer momento.

**Kit de Admissão (ZIP):** Clique em **"🎁 Gerar Kit Admissão Completo (ZIP)"** para baixar todos os documentos-padrão do funcionário (ficha de registro, CTPS, termo de responsabilidade etc.) em um único arquivo ZIP.

### 6.3 Aba — Assistente de Admissão

O Assistente guia o usuário passo a passo no processo de admissão de um novo colaborador, garantindo que nenhuma etapa seja esquecida:

1. **Dados Pessoais** — CPF, RG, data de nascimento, endereço
2. **Dados Contratuais** — cargo, salário, regime, data de admissão
3. **Benefícios** — VT, plano de saúde, dependentes
4. **Documentos** — checklist de documentos exigidos
5. **eSocial** — geração automática do evento S-2200

---

## 7. Folha de Pagamento

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 💰 Folha de Pagamento

### 7.1 Calculando a Folha

1. Selecione o **Mês de Referência** no campo de seleção (ex: `04/2026`)
2. Clique em **"🔄 Calcular Todos"** para processar todos os funcionários ativos de uma vez

O sistema calcula automaticamente para cada funcionário:
- **INSS** (tabela progressiva vigente)
- **IRRF** (após deduções de INSS e dependentes)
- **Desconto VT** (limitado a 6% do salário base)
- **Desconto Plano de Saúde** (se cadastrado)
- **Horas Extras** (50% e 100% — se lançadas no Gestão de Ponto)
- **Faltas** (desconto proporcional — se lançadas no Gestão de Ponto)
- **Salário Líquido**

### 7.2 Ajustes Manuais por Funcionário

Para personalizar a folha de um funcionário específico:

1. Após calcular, localize o funcionário na lista e clique no expander com o nome dele
2. Na seção **"Itens Extras"**, clique em **"➕ Adicionar Item"**
3. Escolha o tipo: **Provento** (aumenta o líquido) ou **Desconto** (diminui o líquido)
4. Digite a descrição e o valor
5. Clique em **"🔄 Recalcular"** para atualizar o líquido

**Exemplos de uso:**
- Bônus por desempenho → Tipo Provento
- Desconto de uniforme → Tipo Desconto
- Adiantamento salarial → Tipo Desconto
- Prêmio de produção → Tipo Provento

### 7.3 Visualizando o Resultado

Para cada funcionário calculado, o sistema exibe:

| Coluna | Descrição |
|---|---|
| Salário Base | Salário contratual |
| INSS | Contribuição previdenciária do empregado |
| IRRF | Imposto de Renda Retido na Fonte |
| VT | Desconto do Vale-Transporte |
| Plano de Saúde | Desconto do plano |
| Outros Descontos | Itens extras tipo desconto |
| Outros Proventos | Itens extras tipo provento |
| **Líquido** | **Valor a receber** |

### 7.4 Encargos Patronais

No resumo da folha, o sistema calcula os custos do **empregador**:
- **Encargos Patronais** = Salário Base × (INSS Patronal + RAT + Terceiros)
- **FGTS Patronal** = Salário Base × 8%
- **Custo Total Estimado** = Folha + Encargos + FGTS

> As alíquotas são configuradas em **Configurações da Empresa** para cada CNPJ.

### 7.5 Contracheque PDF

Após o cálculo, clique em **"📄 Contracheque"** ao lado de qualquer funcionário para baixar o holerite em PDF com todos os itens detalhados, pronto para entrega.

### 7.6 Exportar Folha Analítica

Clique em **"📊 Folha Analítica PDF"** para gerar um relatório consolidado com todos os funcionários do mês em uma única folha.

---

## 8. Gestão de Ponto

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 🕒 Gestão de Ponto

Registre horas extras e faltas que serão automaticamente consideradas no próximo cálculo de folha.

### 8.1 Lançar Ocorrências

1. Selecione o **Funcionário** e o **Mês de Referência**
2. Preencha os campos:
   - **Horas Extras 50%**: horas trabalhadas além da jornada em dias úteis
   - **Horas Extras 100%**: horas em domingos, feriados ou período noturno
   - **Faltas (Dias)**: dias de ausência sem justificativa
   - **Observações**: registro livre (atestados, justificativas etc.)
3. Clique em **"💾 Salvar Lançamentos"**

### 8.2 Impacto na Folha de Pagamento

Ao calcular a folha de um mês, o sistema busca automaticamente os lançamentos de ponto daquele período:
- **HE 50%:** Valor da hora × 1,5 × quantidade
- **HE 100%:** Valor da hora × 2,0 × quantidade
- **Faltas:** Salário ÷ 30 × dias de falta (desconto)

> O valor da hora é calculado como: Salário Base ÷ 220 horas mensais.

### 8.3 Resumo do Mês

Na parte inferior da tela, uma tabela mostra todos os funcionários com lançamentos no mês selecionado, facilitando a conferência antes do cálculo da folha.

---

## 9. 13º Salário

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 🎄 13º Salário

### 9.1 Tipos de Cálculo

**Adiantamento (1ª Parcela) — até 30/novembro**
- Calculado sobre o salário base sem descontos de INSS e IRRF
- Percentual configurável (padrão: 50%)
- Proporcional ao número de avos trabalhados no ano

**Final (2ª Parcela) — até 20/dezembro**
- Calculado sobre o salário base com descontos de INSS e IRRF
- Considera os avos do ano completo

### 9.2 Como Calcular

1. Selecione o **Ano** de referência
2. Escolha o **Tipo**: Adiantamento ou Final
3. Selecione o **Mês de Pagamento**
4. Para adiantamento, ajuste o **Percentual** (slider de 10% a 100%)
5. Clique em **"🔄 Calcular 13º para Todos"**

### 9.3 Cálculo de Avos

O sistema calcula automaticamente os avos com base na data de admissão:
- Cada mês trabalhado (com 15 dias ou mais) equivale a 1/12 do 13º
- Admitido em outubro: 3 avos (out/nov/dez)
- Admitido em janeiro: 12 avos

### 9.4 Documentos Gerados

Após o cálculo, clique em **"📄 13º PDF"** para gerar o documento de pagamento do décimo terceiro com todos os detalhes de cálculo.

---

## 10. Férias

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 🏖️ Férias

### 10.1 Período Aquisitivo e Concessivo

- **Período Aquisitivo:** 12 meses de trabalho contínuo para adquirir o direito a 30 dias de férias
- **Período Concessivo:** Os 12 meses seguintes para que o empregador conceda as férias
- O Dashboard alerta sobre funcionários com férias a vencer

### 10.2 Como Calcular as Férias

1. Selecione o **Funcionário** (apenas ativos aparecem)
2. Informe a **Data de Início das Férias**
3. Defina a **Quantidade de Dias** (máximo 30)
4. Marque as opções desejadas:
   - **Abono Pecuniário (vender 10 dias):** O funcionário recebe por 10 dias adicionais em dinheiro
   - **13º nas Férias:** Pagar a 1ª parcela do 13º junto com as férias
5. Clique em **"🔄 Calcular Férias"**

### 10.3 Componentes do Cálculo

| Componente | Fórmula |
|---|---|
| Férias Base | Salário ÷ 30 × dias de férias |
| 1/3 Constitucional | Férias Base ÷ 3 |
| Abono Pecuniário | Salário ÷ 30 × 10 |
| 13º Proporcional | Salário ÷ 12 × avos |
| INSS | Sobre total bruto (tabela progressiva) |
| IRRF | Sobre total − INSS − deduções |

### 10.4 eSocial Automático

Ao confirmar o cálculo de férias, o sistema adiciona automaticamente o evento **S-2230 (Afastamento Temporário)** à fila do eSocial com as datas corretas.

### 10.5 Recibo de Férias PDF

Clique em **"📄 Recibo de Férias PDF"** para gerar o documento oficial com os valores discriminados, pronto para assinatura.

---

## 11. Rescisão Contratual

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** ⚖️ Rescisão

### 11.1 Tipos de Desligamento Suportados

| Tipo | Aviso Prévio | Multa FGTS |
|---|---|---|
| Sem Justa Causa (com aviso trabalhado) | Sim | 40% |
| Sem Justa Causa (aviso indenizado) | Indenizado | 40% |
| Pedido de Demissão (com aviso trabalhado) | Sim | 0% |
| Pedido de Demissão (sem aviso) | Sem aviso | 0% |
| Acordo entre Partes (art. 484-A CLT) | 50% indenizado | 20% |
| Justa Causa (empregador) | Não | 0% |
| Justa Causa (empregado — culpa recíproca) | Não | 20% |

### 11.2 Como Calcular a Rescisão

1. Selecione o **Funcionário**
2. Informe a **Data de Demissão**
3. Escolha o **Tipo de Rescisão**
4. Configure o **Aviso Prévio** (trabalhado ou indenizado)
5. Informe o **Saldo de FGTS** do trabalhador (obtido no extrato do FGTS)
6. Marque se há **Férias Vencidas** a pagar
7. Clique em **"🔄 Calcular Rescisão"**

### 11.3 Verbas Calculadas

| Verba | Quando pagar |
|---|---|
| Saldo de Salário | Sempre |
| Aviso Prévio | Conforme tipo de demissão |
| Férias Proporcionais + 1/3 | Sempre |
| Férias Vencidas + 1/3 | Se houver férias não gozadas |
| 13º Proporcional | Sempre |
| Multa FGTS | Conforme tipo (0%, 20% ou 40%) |

### 11.4 Backup Automático

Antes de processar uma rescisão, o sistema cria automaticamente um backup dos dados. Isso garante que o histórico seja preservado mesmo em caso de erro.

### 11.5 Termo de Rescisão PDF

Após o cálculo, clique em **"📄 Termo de Rescisão PDF"** para gerar o TRCT (Termo de Rescisão do Contrato de Trabalho) com todos os valores e assinaturas.

---

## 12. eSocial — Painel de Transmissão

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 📤 eSocial — Painel de Transmissão

### 12.1 Visão Geral do eSocial no Sistema

O módulo eSocial gerencia os eventos trabalhistas no formato exigido pelo governo federal. O sistema gera os XMLs nos leiautes oficiais e mantém uma fila de controle de transmissão.

### 12.2 Fila de Eventos

A aba **"Fila de Eventos"** exibe todos os eventos pendentes e transmitidos, com os seguintes status:

| Status | Descrição |
|---|---|
| ⏳ Pendente | Evento gerado, aguardando transmissão |
| 🔄 Aguardando | Em processamento |
| ✅ Transmitido | Evento enviado e aceito |
| ❌ Rejeitado | Erro na transmissão — verificar dados |
| 🚫 Cancelado | Evento cancelado manualmente |

### 12.3 Adicionar Evento Manualmente

1. Acesse a aba **"Adicionar Evento"**
2. Selecione o **Tipo de Evento**:
   - S-1200 — Remuneração do Trabalhador (mensal)
   - S-1210 — Pagamentos de Rendimentos
   - S-2200 — Cadastramento Inicial / Admissão
   - S-2205 — Alteração de Dados Cadastrais
   - S-2206 — Alteração de Contrato de Trabalho
   - S-2230 — Afastamento Temporário (férias)
   - S-2299 — Desligamento
3. Selecione o funcionário relacionado
4. Adicione observações se necessário
5. Clique em **"➕ Adicionar à Fila"**

### 12.4 Geração de XMLs

Na aba **"Geração de XMLs"**, você pode gerar os arquivos XML para transmissão:

**S-1200 — Folha do Mês**
1. Selecione o mês de referência
2. Clique em **"⚙️ Gerar S-1200"**
3. Baixe o arquivo XML gerado

**S-2200 — Admissão**
1. Selecione o funcionário admitido
2. Clique em **"⚙️ Gerar S-2200"**

**S-2299 — Desligamento**
1. Selecione o funcionário desligado
2. Informe a data de desligamento e o tipo
3. Clique em **"⚙️ Gerar S-2299"**

> **Nota:** Os XMLs gerados pelo sistema são baseados nos leiautes oficiais do eSocial. Recomenda-se validar os arquivos no Portal do eSocial antes da transmissão definitiva.

### 12.5 Atualização de Status

Para atualizar o status de um evento na fila:
1. Localize o evento
2. Use o seletor de status para escolher o novo estado
3. Clique em **"Atualizar"**

---

## 13. Relatórios e PDFs

> **Acesso:** Todos os perfis (com filtro por empresa)
> **Menu:** 📄 Relatórios

### 13.1 Tipos de Relatórios Disponíveis

| Relatório | Descrição |
|---|---|
| **Contracheque** | Holerite individual por funcionário e mês |
| **Folha Analítica** | Consolidado de todos os funcionários em um mês |
| **Ficha de Cadastro** | Dados cadastrais completos do funcionário |
| **Ficha Financeira Anual** | Histórico de pagamentos do ano inteiro |
| **Resumo Geral da Folha** | Totais e encargos patronais por mês |
| **Memória de Cálculo** | Detalhamento item a item do cálculo |
| **Recibo de Férias** | Demonstrativo de pagamento de férias |
| **Termo de Rescisão** | TRCT completo para desligamento |
| **Décimo Terceiro** | Demonstrativo do 13º salário |

### 13.2 Como Gerar um Relatório

1. Acesse **"📄 Relatórios"** no menu
2. Marque **"Incluir Inativos"** se desejar ver funcionários desligados
3. Selecione o funcionário desejado
4. Escolha o tipo de relatório e o período (mês/ano)
5. Clique no botão de geração correspondente
6. Clique em **"⬇️ Baixar PDF"** quando o botão aparecer

### 13.3 Conteúdo dos PDFs

Todos os PDFs gerados incluem automaticamente:
- **Cabeçalho** com Razão Social, CNPJ e endereço da empresa da sessão ativa
- **Data de geração** e versão do sistema
- **Dados do funcionário** com cargo e departamento
- **Valores calculados** com discriminação de cada componente

---

## 14. Importação de Dados

> **Acesso:** Perfil **coordenador** ou superior
> **Menu:** 📥 Importação de Dados

### 14.1 Importar Funcionários em Lote

Use esta funcionalidade para cadastrar vários funcionários de uma vez a partir de uma planilha CSV.

**Passo 1 — Baixar o modelo**
Clique em **"⬇️ Baixar Modelo CSV (Cadastro)"** para obter a planilha com as colunas corretas.

**Passo 2 — Preencher a planilha**
Abra o arquivo no Excel ou LibreOffice e preencha uma linha por funcionário:

| Coluna | Obrigatório | Formato |
|---|---|---|
| nome | ✅ | Texto |
| cpf | ✅ | Somente números ou formatado |
| rg | Não | Texto |
| data_nascimento | Não | AAAA-MM-DD |
| data_admissao | Não | AAAA-MM-DD |
| cargo | Não | Texto |
| departamento | Não | Texto |
| salario_base | Não | Número (ex: 1800.00) |
| dependentes | Não | Número inteiro |

**Passo 3 — Importar**
1. Clique em **"Browse files"** e selecione o arquivo CSV preenchido
2. Verifique a prévia dos dados exibida na tela
3. Clique em **"🚀 Confirmar Importação de Cadastro"**

O sistema valida cada CPF e ignora linhas com CPF inválido ou já cadastrado na empresa.

### 14.2 Importar Itens de Folha

Permite lançar proventos e descontos para múltiplos funcionários ao mesmo tempo (ex: bônus coletivo, desconto de uniforme para todos).

**Modelo CSV para itens de folha:**

| Coluna | Descrição |
|---|---|
| cpf | CPF do funcionário |
| mes_ref | Mês no formato MM/AAAA |
| tipo | `provento` ou `desconto` |
| descricao | Nome do item (ex: Bônus Meta) |
| valor | Valor em reais |

---

## 15. Configuração de Tabelas INSS/IRRF

> **Acesso:** Somente perfil **admin**
> **Menu:** ⚙️ Configuração de Tabelas

### 15.1 Para que Serve

O governo federal atualiza anualmente as faixas e alíquotas do INSS e do IRRF. Esta tela permite que o administrador atualize essas tabelas sem precisar de suporte técnico.

### 15.2 Tabela INSS

Exibe as faixas de contribuição em formato editável:

| Campo | Descrição |
|---|---|
| limite | Teto da faixa em R$ |
| aliquota | Percentual decimal (ex: 0.075 = 7,5%) |
| Teto da Base | Valor máximo sobre o qual o INSS incide |

### 15.3 Tabela IRRF

Exibe as faixas do imposto de renda:

| Campo | Descrição |
|---|---|
| limite | Teto da faixa em R$ |
| aliquota | Percentual decimal (ex: 0.075 = 7,5%) |
| deducao | Parcela a deduzir da faixa em R$ |
| Dedução por Dependente | Valor fixo de dedução por cada dependente |

### 15.4 Como Atualizar

1. Edite os valores diretamente na tabela interativa
2. Clique em **"💾 Salvar Todas as Alterações"**
3. Os novos valores valem para **todos os cálculos futuros**

> **Atenção:** Folhas já calculadas não são recalculadas automaticamente. Se precisar recalcular, acesse a Folha de Pagamento e clique em "Calcular Todos" novamente para o mês desejado.

### 15.5 Tabelas Vigentes para 2026

**INSS (Progressivo):**

| Faixa | Alíquota |
|---|---|
| Até R$ 1.518,00 | 7,5% |
| De R$ 1.518,01 até R$ 2.793,88 | 9,0% |
| De R$ 2.793,89 até R$ 4.190,83 | 12,0% |
| De R$ 4.190,84 até R$ 8.157,41 | 14,0% |

**IRRF (Tabela Mensal):**

| Base de Cálculo | Alíquota | Parcela a Deduzir |
|---|---|---|
| Até R$ 2.259,20 | Isento | — |
| De R$ 2.259,21 até R$ 2.826,65 | 7,5% | R$ 169,44 |
| De R$ 2.826,66 até R$ 3.751,05 | 15,0% | R$ 381,44 |
| De R$ 3.751,06 até R$ 4.664,68 | 22,5% | R$ 662,77 |
| Acima de R$ 4.664,68 | 27,5% | R$ 896,00 |

**Dedução por dependente:** R$ 189,59 por dependente

---

## 16. Configurações da Empresa

> **Acesso:** Somente perfil **admin**
> **Menu:** 🏢 Configurações da Empresa

Esta tela configura os parâmetros da empresa **da sessão ativa**. Cada empresa possui suas próprias configurações.

### 16.1 Dados Cadastrais

- **Razão Social:** Nome que aparece nos documentos e PDFs
- **CNPJ:** Aparece no cabeçalho de todos os PDFs
- **Endereço:** Cidade e estado para identificação nos documentos

### 16.2 Regime Tributário

Selecione o regime da empresa:
- **Simples Nacional:** Empresas no Simples (exceto Anexo IV) normalmente colocam 0% no INSS Patronal
- **Lucro Presumido:** INSS Patronal padrão de 20%
- **Lucro Real:** INSS Patronal padrão de 20%

### 16.3 Encargos Patronais

Configure as alíquotas para cálculo do custo total do empregador:

| Campo | Descrição | Exemplo |
|---|---|---|
| INSS Patronal (%) | Contribuição previdenciária do empregador | 20% |
| RAT / FAP (%) | Risco Ambiental do Trabalho | 1% a 3% |
| Terceiros (%) | SESC, SENAC, SEBRAE, INCRA etc. | 5,8% |

> Essas alíquotas são usadas no cálculo de **Encargos Patronais** exibido na Folha de Pagamento e no PDF de Resumo da Folha.

---

## 17. Backup e Restauração

> **Acesso:** Somente perfil **admin**
> **Menu:** 💾 Backup e Restauração

### 17.1 Backup Manual

Na tela de Backup e Restauração, clique em **"📦 Criar Backup Agora"**. O sistema compacta toda a pasta `data_dp/` em um arquivo ZIP com timestamp.

Também é possível criar um backup rápido pela barra lateral, clicando no expander **"💾 Backup"**.

### 17.2 Backup Automático

O sistema cria backups automáticos antes de operações críticas:
- Antes de processar uma **rescisão**
- Antes de **excluir um funcionário**
- Antes de uma **restauração**

### 17.3 Lista de Backups

A tela exibe os últimos 10 backups (o sistema mantém apenas os 10 mais recentes):
- Data e hora da criação
- Motivo do backup (manual, antes_rescisão, restauração etc.)
- Tamanho do arquivo

### 17.4 Restaurar um Backup

> **⚠️ Atenção:** A restauração substitui todos os dados atuais. Crie um backup do estado atual antes de restaurar.

1. Selecione o backup desejado na lista
2. Clique em **"🔄 Restaurar"**
3. Confirme a operação
4. O sistema substituirá os dados e reiniciará

---

## 18. Logs do Sistema

> **Acesso:** Somente perfil **admin**
> **Menu:** 📋 Logs do Sistema

### 18.1 O que é Registrado

Toda ação relevante no sistema gera uma linha de log com:
- **Timestamp** (data e hora exata)
- **Nível** (INFO, WARNING, ERROR)
- **Usuário** que executou a ação
- **Descrição** da ação

Exemplos de eventos registrados:
- Login e logout de usuários
- Cadastro, edição e exclusão de funcionários
- Cálculos de folha, 13º, férias e rescisão
- Geração de XMLs do eSocial
- Criação e restauração de backups
- Alterações de senha
- Tentativas de login fracassadas

### 18.2 Filtros

- **Nível:** Filtre por INFO, WARNING ou ERROR
- **Buscar texto:** Pesquise por nome de usuário, ação ou qualquer texto
- **Últimas N linhas:** Limite a quantidade de linhas exibidas

### 18.3 Download do Log

Clique em **"⬇️ Baixar Log"** para exportar o arquivo de log do mês selecionado.

### 18.4 Imutabilidade dos Logs

Os logs são gravados em arquivo e **não podem ser apagados pela interface do sistema**. Isso garante o rastreamento completo de todas as operações para fins de auditoria.

---

## 19. Regras de Cálculo Vigentes (2026)

### 19.1 INSS — Contribuição Previdenciária

O cálculo é **progressivo** (igual ao IRPF): cada faixa de salário é tributada pela sua alíquota correspondente, e o total é a soma das contribuições em cada faixa.

**Exemplo** para salário de R$ 3.000,00:
- R$ 1.518,00 × 7,5% = R$ 113,85
- (R$ 2.793,88 − R$ 1.518,00) × 9% = R$ 114,83
- (R$ 3.000,00 − R$ 2.793,88) × 12% = R$ 24,74
- **Total INSS = R$ 253,42**

### 19.2 IRRF — Imposto de Renda Retido na Fonte

Calculado sobre a **base de cálculo** = Salário Bruto − INSS − (Nº dependentes × R$ 189,59)

**Exemplo** para salário líquido de INSS de R$ 2.500,00, 1 dependente:
- Base = R$ 2.500,00 − R$ 189,59 = R$ 2.310,41
- Faixa de 7,5%: R$ 2.310,41 × 7,5% − R$ 169,44 = R$ 3,94

### 19.3 Vale-Transporte

O desconto de VT é limitado a **6% do salário base**:
- Se o VT mensal do funcionário for menor que 6% do salário → desconta o valor real do VT
- Se o VT mensal for maior que 6% do salário → desconta apenas 6% do salário

**Exemplo:** Salário R$ 1.800,00 | VT declarado R$ 200,00
- 6% de R$ 1.800,00 = R$ 108,00
- Como R$ 200,00 > R$ 108,00 → desconta R$ 108,00

### 19.4 FGTS

- **Empregado:** Não tem desconto na folha (o FGTS não é deduzido do salário)
- **Empregador:** Deposita 8% do salário bruto na conta vinculada do FGTS
- O sistema calcula o FGTS patronal no resumo da folha, mas **não gera DARF automaticamente**

### 19.5 13º Salário

**Fórmula:** Salário Base ÷ 12 × avos trabalhados

- Cada mês com 15 dias ou mais = 1 avo
- Mês com menos de 15 dias trabalhados = não conta
- INSS e IRRF incidem normalmente na 2ª parcela

### 19.6 Férias

| Componente | Fórmula |
|---|---|
| Férias (30 dias) | Salário ÷ 30 × 30 |
| 1/3 Constitucional | Férias ÷ 3 |
| Abono (10 dias) | Salário ÷ 30 × 10 |
| Total Bruto | Férias + 1/3 + Abono (se houver) |

---

## 20. Segurança e Boas Práticas

### 20.1 Criptografia de Dados

- Os arquivos `funcionarios.json` e `usuarios.json` são criptografados com **Fernet (AES-256)** em repouso
- A chave de criptografia é gerada automaticamente e armazenada em `data_dp/.master.key`
- **Não exclua o arquivo `.master.key`** — sem ele, os dados criptografados não podem ser lidos

### 20.2 Senhas

- Todas as senhas são armazenadas como **hash SHA-256 com salt individual**
- Nunca são gravadas em texto puro
- Mínimo de 8 caracteres recomendado

### 20.3 Recomendações de Segurança

- **Altere as senhas padrão** (`123456`) imediatamente após o primeiro acesso
- **Crie um usuário por pessoa** — nunca compartilhe credenciais
- **Mantenha backups** em local seguro, fora do servidor do sistema
- **Restrinja o acesso admin** ao menor número de pessoas possível
- **Monitore os logs** periodicamente para detectar acessos suspeitos
- Em produção, use conexão **HTTPS** (o Docker com Nginx e Let's Encrypt já provê isso)

### 20.4 Dados Sensíveis

O sistema armazena dados pessoais sensíveis (CPF, salário, dados bancários). Certifique-se de que o acesso ao servidor está protegido e que os backups também estão seguros, em conformidade com a **LGPD (Lei Geral de Proteção de Dados)**.

---

## 21. Perguntas Frequentes

**P: Esqueci minha senha. Como recuperar?**
R: O sistema não possui recuperação de senha por e-mail. Um administrador deve acessar **Gerenciar Usuários**, excluir o usuário e criar um novo com nova senha.

**P: Como adicionar uma segunda empresa?**
R: Acesse **🏢 Cadastro de Empresas** (menu admin) e cadastre a nova empresa. Depois crie ou edite os usuários vinculando-os à nova empresa.

**P: Um funcionário da empresa A pode ver dados da empresa B?**
R: Não. Cada usuário vinculado a uma empresa só acessa os dados dela. Apenas o Admin Global (sem empresa vinculada) tem visão de todas.

**P: O sistema conecta direto no Portal do eSocial para transmitir?**
R: Não. O sistema gera os arquivos XML no formato correto do eSocial. A transmissão deve ser feita manualmente pelo Portal do eSocial ou por software de transmissão certificado.

**P: Os gráficos do Dashboard não aparecem. O que fazer?**
R: Os gráficos exigem a biblioteca Plotly. Execute `pip install plotly` no ambiente do sistema.

**P: Posso usar o sistema em múltiplos computadores ao mesmo tempo?**
R: Sim, se o sistema estiver em um servidor (Docker em VPS). O acesso simultâneo é suportado pelo Streamlit. Em modo local, apenas uma sessão por vez é recomendada.

**P: Como atualizo as tabelas de INSS e IRRF para o próximo ano?**
R: Acesse **⚙️ Configuração de Tabelas** (menu admin) e atualize os valores conforme a legislação publicada. As folhas calculadas antes da atualização não são alteradas automaticamente.

**P: O backup inclui os documentos dos funcionários (PDFs, fotos)?**
R: Sim. O backup compacta toda a pasta `data_dp/`, incluindo a subpasta `documentos/` com todos os arquivos enviados.

**P: Como excluir um funcionário desligado sem perder o histórico?**
R: Recomenda-se apenas **inativar** o funcionário (situação = Inativo) em vez de excluir. A exclusão é irreversível. Funcionários inativos não aparecem nos cálculos mas mantêm o histórico acessível nos Relatórios.

**P: Posso importar funcionários de outra empresa via CSV e já vinculá-los à empresa correta?**
R: Sim. Ao importar, o sistema vincula automaticamente os funcionários à empresa da sessão ativa no momento da importação.

---

*Manual gerado automaticamente pelo DPMaster Pro — Não edite diretamente este arquivo.*
*Última atualização: {data_atual}*
"""

# ==================== FUNÇÃO PRINCIPAL ====================

def gerar_manuais():
    """Gera/atualiza todos os manuais automaticamente"""
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    Path("docs").mkdir(exist_ok=True)

    conteudo_utilizacao = MANUAL_UTILIZACAO.format(data_atual=data_atual)

    with open("docs/manual_utilizacao.md", "w", encoding="utf-8") as f:
        f.write(conteudo_utilizacao)

    print("✅ Manual de Utilização gerado com sucesso: docs/manual_utilizacao.md")

    try:
        from app_dp import gerar_manual_sistema_pdf
        buffer = gerar_manual_sistema_pdf()
        if buffer:
            with open("docs/manual_utilizacao.pdf", "wb") as f:
                f.write(buffer.getvalue())
            print("✅ Manual em PDF gerado: docs/manual_utilizacao.pdf")
    except Exception as e:
        print(f"⚠️ Não foi possível gerar PDF automaticamente: {e}")
        print("   → Use o botão dentro do sistema para gerar o PDF completo.")

    with open("docs/changelog.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d')} - Atualização\n")
        f.write("- Documentação atualizada automaticamente via script\n")

    print("\n🎉 Documentação atualizada com sucesso!")


if __name__ == "__main__":
    gerar_manuais()
