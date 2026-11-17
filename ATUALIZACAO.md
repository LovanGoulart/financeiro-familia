# Financeiro Familiar — atualização de 17/11/2026

## O que mudou

- Avisos flutuantes sobre alterações de despesas, categorias, lista de compras e usuários da mesma família.
- Eventos em tempo real por SSE, com consulta automática a cada 2 segundos como alternativa quando o servidor bloquear streaming. Não exige Redis ou banco adicional.
- Botão **Ativar som**, com sinal de teste e preferência salva neste navegador. Cada evento recebido toca uma vez, sem repetição na reconexão; operações do próprio usuário usam a confirmação da tela.
- Resumo da página inicial em duas colunas somente no celular (até 768 px). No desktop, distribuição original dos cards.
- Início, Despesas, Relatórios e API abrem no **mês seguinte ao atual**, considerando o horário de Brasília. Em novembro/2026, a abertura padrão será dezembro/2026; em dezembro/2026, janeiro/2027. Os filtros continuam disponíveis.
- Novas despesas sugerem a data de pagamento do mês seguinte. A data é o vencimento/pagamento, não a data da compra. Compras à vista podem usar outra data. Lançamentos já existentes não foram deslocados.
- Valores em reais, vírgula decimal, datas dd/mm/aaaa, filtros mm/aaaa, meses e textos em português. O banco e a API mantêm os formatos técnicos adequados para armazenamento e integração.
- Instalação PWA com aviso flutuante, ícones e abertura como aplicativo.

## Atualizar sem perder os dados

1. Pare o sistema e faça uma cópia da pasta atual, especialmente `database/finance.db`.
2. Extraia este ZIP em outra pasta. Para atualizar uma instalação existente, copie os arquivos de código, `templates/`, `static/`, `models/` e `requirements.txt` para ela. **Não substitua o banco que está em uso pelo banco incluído no ZIP**: o ZIP contém a cópia recebida nesta análise, que pode estar mais antiga que sua instalação.
3. Na pasta do projeto, execute:

```bash
python -m pip install -r requirements.txt
python app.py
```

4. Abra `http://127.0.0.1:5000`. Faça login normalmente. A primeira inicialização adiciona a tabela de eventos, índices e o campo de ajuste de centavos às parcelas. Não apaga usuários, categorias, despesas ou compras.
5. No navegador, atualize a página com Ctrl+F5. Clique em **Ativar som**.

Use Python 3.10 ou superior. `tzdata` está nas dependências para o fuso brasileiro funcionar também no Windows.

## Instalação do aplicativo

Em uma hospedagem, use **HTTPS**. Localmente, `localhost` e `127.0.0.1` também permitem os recursos PWA.

No Chrome/Edge compatível, o aviso aparece quando o navegador libera a instalação. Após a confirmação, o sistema grava a instalação neste navegador e oculta o convite nas próximas visitas. Abrir pelo ícone instalado também registra essa condição. Recusar o convite o adia por 24 horas.

No iPhone/iPad, o aviso orienta a usar **Compartilhar → Adicionar à Tela de Início**. Depois abra pelo ícone ou toque em **Já instalei**. Não existe detecção universal de instalações feitas por outros navegadores/perfis. A limpeza dos dados do navegador remove o registro local.

O app exige conexão para acessar as finanças. O service worker armazena somente ícones públicos; não mantém cópias offline dos dados financeiros.

## Notificações e som

Abra duas sessões com usuários da mesma família. Em uma delas, ative o som; na outra, cadastre uma despesa. A primeira deve receber um aviso e atualizar a consulta automaticamente.

Os avisos funcionam com o site/app aberto. Esta versão não inclui Web Push com o aplicativo fechado. O navegador pode suspender abas em segundo plano; ao voltar à aba, o sistema consulta os eventos pendentes. Formulários com alterações e modais abertos não são descartados por atualizações automáticas.

O som depende da interação do usuário e das permissões/restrições do navegador e do aparelho. Se ele estiver bloqueado, interaja com a página ou desative e reative **Som ativado**.

## Hospedagem

- Mantenha o banco em disco persistente e a pasta `instance/` gravável; uma chave de sessão é gerada e mantida ali quando `SECRET_KEY` não está definida.
- Em produção, configure uma `SECRET_KEY` longa, aleatória e estável por variável de ambiente. Todos os processos devem usar a mesma chave. Não publique a chave nem o banco em repositórios públicos.
- Com HTTPS, defina `COOKIE_SECURE=1`. Não ative isso no acesso HTTP local.
- Opcional: `DATABASE_PATH` pode apontar para o caminho absoluto do seu banco existente.
- Use um servidor WSGI em produção. Para SSE, habilite concorrência por threads e streaming sem buffering. Em servidores que não suportam SSE, a consulta de reserva continua funcionando; a capacidade depende da quantidade de usuários e dos workers disponíveis.
- No PythonAnywhere, aponte o arquivo WSGI para `from app import app as application`, com a pasta do projeto no `sys.path`. Recarregue a aplicação após instalar as dependências.

## Recuperar uma senha

O administrador da família pode alterar a senha dos membros em **Usuários**. Se o próprio administrador perder o acesso, o responsável pela hospedagem pode executar:

```bash
python reset_password.py
```

O comando solicita nome de usuário, nova senha e confirmação, sem mostrar a senha no terminal. A antiga recuperação pública por senha fixa foi removida.

## Reexecutar os testes

```bash
python -m pip install pytest
python -m pytest -q tests/test_system.py
```

Para as verificações de JavaScript em DOM simulado, use Node.js compatível com o jsdom informado em `tests/package.json`:

```bash
npm --prefix tests install
npm --prefix tests test
```

Os testes usam bancos temporários. Não alteram seu banco familiar.
