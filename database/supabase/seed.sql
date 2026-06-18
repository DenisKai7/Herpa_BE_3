insert into public.quiz_subjects(slug,title,description,sort_order) values
('kimia-dasar','Kimia Dasar','Pembelajaran kimia tingkat SMA hingga universitas awal',1),
('fitokimia','Fitokimia','Senyawa aktif dan analisis bahan alam',2)
on conflict(slug) do update set title=excluded.title;

with s as (select id from public.quiz_subjects where slug='kimia-dasar')
insert into public.quiz_modules(subject_id,slug,title,description,sort_order)
select id,'sistem-periodik','Sistem Periodik Unsur','Struktur tabel periodik dan tren sifat unsur',1 from s
on conflict(slug) do update set title=excluded.title;

with m as (select id from public.quiz_modules where slug='sistem-periodik')
insert into public.quiz_levels(module_id,level_number,title,passing_score,xp_reward)
select id,n,case n when 1 then 'Pengenalan' when 2 then 'Pemahaman' when 3 then 'Penerapan' when 4 then 'Analisis' else 'Mastery Challenge' end,70,20+n*5
from m cross join generate_series(1,5) n on conflict(module_id,level_number) do nothing;

with l as (select id from public.quiz_levels where level_number=1 and module_id=(select id from public.quiz_modules where slug='sistem-periodik') limit 1),
q as (insert into public.quiz_questions(level_id,question_type,prompt,explanation,correct_answer,difficulty)
select id,'multiple_choice','Unsur dengan simbol Na adalah ...','Na adalah simbol natrium.', '["natrium"]'::jsonb,1 from l returning id)
insert into public.quiz_question_options(question_id,option_key,label,is_correct,sort_order)
select id,x.key,x.label,x.correct,x.ord from q cross join (values ('natrium','Natrium',true,1),('nitrogen','Nitrogen',false,2),('neon','Neon',false,3),('nikel','Nikel',false,4)) x(key,label,correct,ord);
