CREATE TABLE candidate
  (committee_id varchar(10),
   lastname varchar(50),
   firstname varchar(50),
   party varchar(6),
   city varchar(20),
   state varchar(2),
   zip integer,
   cand_id varchar(10),
   district varchar(2),
   CONSTRAINT pk_candidate PRIMARY KEY (committee_id)
   );

.separator ","
.import candidate.csv candidate


CREATE TABLE contribution
  (cand_id varchar(10),
   amount integer,
   city varchar(20),
   state varchar(10),
   zip integer,
   month integer,
   year integer,
   CONSTRAINT fk_contribution FOREIGN KEY (cand_id)
   REFERENCES candidate (cand_id)
   );

.import contributions.csv contribution