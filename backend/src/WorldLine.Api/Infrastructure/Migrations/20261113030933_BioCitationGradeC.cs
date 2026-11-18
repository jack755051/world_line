using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class BioCitationGradeC : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_person_role_citations_grade",
                table: "person_role_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_person_position_citations_grade",
                table: "person_position_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_paragraph_citations_grade",
                table: "leader_bio_paragraph_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations");

            migrationBuilder.AddCheckConstraint(
                name: "ck_person_role_citations_grade",
                table: "person_role_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B', 'C')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_person_position_citations_grade",
                table: "person_position_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B', 'C')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_paragraph_citations_grade",
                table: "leader_bio_paragraph_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B', 'C')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B', 'C')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_person_role_citations_grade",
                table: "person_role_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_person_position_citations_grade",
                table: "person_position_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_paragraph_citations_grade",
                table: "leader_bio_paragraph_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations");

            migrationBuilder.AddCheckConstraint(
                name: "ck_person_role_citations_grade",
                table: "person_role_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_person_position_citations_grade",
                table: "person_position_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_paragraph_citations_grade",
                table: "leader_bio_paragraph_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");
        }
    }
}
