CREATE TABLE "users" (
    "id" bigserial   NOT NULL,
    "identity_provider" varchar(15) NOT NULL,
    "external_id" varchar(255)   NOT NULL,
    "name" varchar(255)   NOT NULL,
    "email" varchar(255)   NOT NULL,
    "profile_pic" varchar(255)   NOT NULL,
    "country" char(2) NOT NULL,
    "last_login" timestamp   NOT NULL,
    "created" timestamp   NOT NULL,
    UNIQUE("identity_provider", "external_id"),
    CONSTRAINT "pk_users" PRIMARY KEY (
        "id"
     )
);
CREATE INDEX users_identity_provider_external_id_idx ON users (identity_provider, external_id);
CREATE INDEX "idx_users_email" ON "users" ("email");

CREATE TABLE "albums" (
    "id" bigserial   NOT NULL,
    "owner" bigserial   NOT NULL,
    "name" varchar(255)   NOT NULL,
    "shared" boolean NOT NULL DEFAULT false,
    "uuid" uuid NULL,
    "created" timestamp   NOT NULL,
    UNIQUE("owner", "name"),
    UNIQUE("uuid"),
    CONSTRAINT "pk_albums" PRIMARY KEY (
        "id"
     )
);
CREATE INDEX "idx_albums_owner" ON "albums" ("owner");
CREATE INDEX "idx_albums_uuid" ON "albums" ("uuid");
ALTER TABLE "albums" ADD CONSTRAINT "fk_albums_owner" FOREIGN KEY("owner") REFERENCES "users" ("id");

-- STATUS:
--  P: Pending
--  R: Ready
--  D: Deleted
--  U: Undeleted
-- FLAG:
--  P: Picked
--  R: Rejected
CREATE TABLE "photos" (
    "id" bigserial   NOT NULL,
    "owner" bigserial   NOT NULL,
    "album" bigserial   NOT NULL,
    "hash" char(32)   NOT NULL,
    "phash" char(16),
    "extension" varchar(16)   NOT NULL,
    "flag" char(1),
    "exif_datetime" timestamp   NOT NULL,
    "status" char(1) NOT NULL DEFAULT 'P',
    "created" timestamp   NOT NULL,
    UNIQUE("owner", "hash"),
    CONSTRAINT "pk_photos" PRIMARY KEY (
        "id"
     )
);
CREATE INDEX "idx_photos_owner" ON "photos" ("owner");
CREATE INDEX "idx_photos_album" ON "photos" ("album");
CREATE INDEX "idx_photos_hash" ON "photos" ("hash");
ALTER TABLE "photos" ADD CONSTRAINT "fk_photos_album" FOREIGN KEY("album") REFERENCES "albums" ("id");
ALTER TABLE "photos" ADD CONSTRAINT "fk_photos_owner" FOREIGN KEY("owner") REFERENCES "users" ("id");

CREATE TABLE "photo_metadata" (
    "id" bigserial   NOT NULL,
    "photo" bigserial   NOT NULL,
    "owner" bigserial   NOT NULL,
    "hash" char(32)   NOT NULL,
    "tag" varchar(32) NOT NULL,
    "value" varchar(255),
    UNIQUE("id", "tag"),
    CONSTRAINT "pk_photo_metadata" PRIMARY KEY (
        "id"
     )
);
CREATE INDEX "idx_photo_metadata_owner" ON "photo_metadata" ("tag");
ALTER TABLE "photo_metadata" ADD CONSTRAINT "fk_photo_metadata_photo" FOREIGN KEY("photo") REFERENCES "photos" ("id");
ALTER TABLE "photo_metadata" ADD CONSTRAINT "fk_photo_metadata_owner" FOREIGN KEY("owner") REFERENCES "users" ("id");
