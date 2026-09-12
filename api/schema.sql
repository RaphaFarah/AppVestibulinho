-- Dados de usuário do AppVestibulinho (Postgres / Supabase).
--
-- O banco de questões NÃO vive aqui: ele é estático, gerado por tools/ e
-- servido como arquivo. Aqui fica só o que é insubstituível — quem respondeu
-- o quê. Por isso os dois nunca compartilham o mesmo arquivo ou base: regerar
-- o banco de questões jamais pode apagar histórico.
--
-- A identidade vem de auth.users, tabela gerenciada pelo Supabase Auth.

create extension if not exists pgcrypto;

create table if not exists tentativa (
    id                uuid primary key default gen_random_uuid(),
    usuario_id        uuid not null references auth.users (id) on delete cascade,
    -- id gerado no cliente antes de haver rede: torna o envio idempotente,
    -- então reenviar a mesma prova depois de uma falha não duplica registro
    cliente_id        text not null,
    modo              text not null default 'simulado'
                      check (modo in ('simulado', 'treino')),
    -- semente do sorteio: permite reconstruir exatamente a mesma prova
    semente           bigint not null,
    total_questoes    integer not null check (total_questoes > 0),
    duracao_segundos  integer,
    acertos           integer,
    criado_em         timestamptz not null default now(),
    finalizado_em     timestamptz,
    unique (usuario_id, cliente_id)
);

create table if not exists resposta (
    tentativa_id  uuid not null references tentativa (id) on delete cascade,
    questao_id    text not null,          -- '2022-q44', como no banco estático
    marcada       text check (marcada is null or marcada in ('A','B','C','D','E')),
    correta       boolean,
    segundos      integer,
    primary key (tentativa_id, questao_id)
);

create index if not exists idx_tentativa_usuario on tentativa (usuario_id, criado_em desc);
create index if not exists idx_resposta_questao  on resposta (questao_id);

-- Desempenho por questão, para o aluno ver onde erra mais.
create or replace view v_desempenho as
select t.usuario_id,
       r.questao_id,
       count(*)                                           as respondidas,
       count(*) filter (where r.correta)                   as acertos,
       round(avg(r.segundos)::numeric, 1)                  as segundos_medio
  from resposta r
  join tentativa t on t.id = r.tentativa_id
 group by t.usuario_id, r.questao_id;

-- A API já filtra por usuário, mas RLS garante o isolamento mesmo se o
-- frontend um dia consultar o Postgres direto pelo Supabase.
alter table tentativa enable row level security;
alter table resposta  enable row level security;

drop policy if exists tentativa_propria on tentativa;
create policy tentativa_propria on tentativa
    for all using (usuario_id = auth.uid()) with check (usuario_id = auth.uid());

drop policy if exists resposta_propria on resposta;
create policy resposta_propria on resposta
    for all using (exists (select 1 from tentativa t
                            where t.id = resposta.tentativa_id
                              and t.usuario_id = auth.uid()))
    with check (exists (select 1 from tentativa t
                         where t.id = resposta.tentativa_id
                           and t.usuario_id = auth.uid()));
