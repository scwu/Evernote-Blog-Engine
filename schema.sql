drop table if exists entries;
create table entries (
  created integer primary key,
  title string not null,
  text string not null
);
