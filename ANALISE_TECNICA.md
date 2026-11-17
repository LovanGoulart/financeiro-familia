# Análise técnica — Financeiro Familiar

Revisão do ZIP fornecido em 17/11/2026. Foram inspecionados o aplicativo Flask, modelos SQLite, templates, estilos, JavaScript, autenticação, autorização, cálculos financeiros e rotas de cadastro/consulta/edição/exclusão. Este relatório cobre revisão de código e testes locais; não representa um teste de invasão da hospedagem.

## Diagnóstico e correções

| Área | Problema encontrado | Correção aplicada |
| --- | --- | --- |
| Notificações | Não havia infraestrutura de eventos entre usuários. | Eventos persistidos junto da alteração no SQLite; SSE autenticado por família, reconexão e consulta de reserva. |
| Interface | Confirmações duplicadas no template base e ausência de avisos flutuantes. | Um único fluxo de avisos, texto inserido com `textContent`, fechamento manual e temporizado. |
| Som | Sem controle ou mecanismo de áudio. | Web Audio, ativação por gesto, preferência local, identificação de eventos e supressão de repetição na reconexão. |
| Atualização | Consultas só refletiam alterações após recarregar. | Resumo inicial atualizado por consulta assíncrona; demais consultas recarregam quando não há edição ativa. |
| PWA | Não existiam manifest, service worker ou ícones de instalação. | Manifest pt-BR, ícones 192/512, service worker na raiz e convite adaptado ao navegador. |
| Mês exibido | Padrões usavam o mês atual, inclusive na API. | Próximo mês calculado no fuso America/Sao_Paulo, com virada de ano e filtros preservados. |
| Crédito | A opção antiga movia a data apenas em JavaScript, sem persistir uma condição de crédito. | Campo explícito de data de pagamento/parcela atual, já sugerido para o mês seguinte; nenhum deslocamento silencioso de lançamentos existentes. |
| Padrão brasileiro | Entrada monetária e datas dependiam do formato do navegador; percentuais usavam ponto; o JS tentava interpretar moedas já formatadas. | Entrada dd/mm/aaaa e mm/aaaa, valores com vírgula, formatação BR nos gráficos, remoção da reinterpretação de moedas e tradução dos rótulos em inglês. |
| Home | Estilos concorrentes forçavam uma coluna no celular. | Regra específica de duas colunas para os oito cards de resumo somente no celular (até 768 px), com largura mínima flexível. No desktop, mantida a distribuição original. |
| Recorrências | Frequência semanal gerava apenas um lançamento por mês, podendo omitir semanas. | Geração de todas as ocorrências semanais nas datas corretas, respeitando o início. |
| Parcelas | Divisão arredondada podia somar centavos a mais/menos; a parcela atual era ignorada. | Novas compras divididas em centavos, diferença na última parcela e respeito à numeração informada. Parcelas antigas mantêm os valores cadastrados. |
| Recuperação de senha | Qualquer visitante podia redefinir uma senha conhecida informando o nome de usuário. | Removida redefinição pública; alteração pelo administrador da família ou comando local de manutenção. |
| Isolamento | Edição permitia enviar outro responsável/categoria sem conferir a família; administrador podia alterar senha de outra família. | Validação de responsável/categoria e consulta da senha administrativa restrita à família. |
| CSRF | Formulários e alteração AJAX não tinham proteção. | Token de sessão em formulários POST e cabeçalho da requisição AJAX, verificado no servidor. |
| Entrada inválida | Valores, datas e filtros malformados podiam causar erro 500. | Validação prévia; respostas controladas ou retorno ao formulário. |
| Sessões | Chave aleatória mudava a cada inicialização. | Chave persistida localmente ou definida por ambiente; cookies HttpOnly/SameSite e Secure configurável. |
| Integridade | Exclusão de categoria deixava referência na lista; remoção de usuário deixava autor antigo em despesas. | Limpeza/reassociação das referências antes da exclusão. |
| Erros e HTML | Página 404 autenticada não recebia contexto do usuário; tabela inicial tinha célula aninhada inválida. | Contexto global seguro e correção da estrutura das células. |
| Segurança de saída | Nome de categoria era interpolado em código JavaScript inline. | Serialização JSON com escape no botão de edição. |
| Tema | Apenas o primeiro botão de tema recebia o evento, prejudicando o celular. | Ambos os botões atualizam o tema e os ícones. |

## Validação executada

- **27 testes automatizados de servidor aprovados**, usando bancos temporários: cadastro, login, páginas autenticadas, API, datas BR, virada de ano/fevereiro bissexto, valores inválidos, despesas, parcelas exatas, parcela atual, recorrência semanal/anual, compras, CSRF, isolamento de famílias, redefinição de senha, escape de conteúdo, erro 404 e leitura/reconexão de eventos SSE.
- **13 verificações de interface simulada aprovadas**: conexão, botão de som e sinal de áudio, aviso de alteração, ausência de repetição, atualização do resumo, tratamento de texto inseguro, convite PWA, confirmação de instalação, supressão após instalação, modo standalone e alternativa quando SSE falha.
- Integridade SQLite verificada (`integrity_check: ok`), sem responsáveis órfãos, datas nulas/inválidas detectadas ou lançamentos marcados simultaneamente como recorrentes e parcelados na cópia recebida.
- Sintaxe Python e JavaScript validada. Arquivo do banco recebido preservado, sem uso como base dos testes.
- **Validação visual em navegador real não concluída**: o ambiente bloqueou a inicialização do Chromium por restrição de sockets. A interface foi verificada em DOM simulado, que não substitui uma conferência visual no computador e no celular.
- Instalação nativa em aparelho físico, reprodução audível no dispositivo do usuário e comportamento da hospedagem de produção ainda devem ser conferidos no ambiente final. Nenhuma implantação foi realizada.

## Limites e manutenção recomendada

1. Notificações são eventos do sistema aberto. Alertas com o aplicativo totalmente fechado exigiriam uma etapa adicional de Web Push e gerenciamento de inscrições/chaves.
2. A instalação é reconhecida por eventos do navegador, modo standalone e registro local. Navegadores não oferecem um inventário universal dos apps instalados em outros perfis. No iOS há orientação e confirmação manual.
3. Recursos externos de ícones e gráficos continuam vindo dos CDNs já usados no projeto. Sem acesso a esses serviços, o conteúdo financeiro continua renderizado pelo servidor, mas esses recursos visuais podem faltar.
4. SQLite continua apropriado ao uso familiar de baixa concorrência; faça backups regulares. Em crescimento com muitas famílias simultâneas, avalie PostgreSQL e um mecanismo dedicado de distribuição de eventos. A tabela de notificações cresce com o uso e precisa de política de retenção em instalações maiores.
5. O controle financeiro usa valores REAL existentes no SQLite. A nova divisão de parcelas calcula os centavos com Decimal; uma migração integral para valores inteiros em centavos fica como evolução separada para evitar reinterpretar dados históricos.
6. Adotar limites de tentativas de login e recuperação por e-mail com token expirável é recomendado antes de ampliar o acesso público. A recuperação pública insegura foi eliminada; não foi inventada uma integração de e-mail sem credenciais.
7. O botão de saída original continua como navegação GET; para uma implantação com requisitos de segurança mais rígidos, pode ser migrado para POST. As alterações financeiras e administrativas já exigem token CSRF.
8. A edição/exclusão de registros virtuais continua afetando o lançamento de origem e, portanto, a série de recorrências/parcelas, como no projeto recebido. Não foi criado um modelo de exceções por ocorrência.

## Referências de compatibilidade consultadas

- [MDN: instalação de PWAs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
- [MDN: beforeinstallprompt](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event)
- [web.dev: convite de instalação](https://web.dev/learn/pwa/installation-prompt/)
