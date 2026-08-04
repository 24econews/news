"""The five recurring opinion columnists for 24EcoNews's Mercosur OpEd section."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    slug: str
    lens_short: str
    lens_full: str
    style: str
    bio: str


def _bio(name: str) -> str:
    return (
        f"{name} is one of 24EcoNews's five recurring opinion columnists, "
        "each representing a distinct editorial perspective on Mercosur affairs."
    )


PERSONAS = [
    Persona(
        name="Ricardo Almeida",
        slug="ricardo-almeida",
        lens_short="Market-liberal / fiscal conservative",
        lens_full=(
            "A market-liberal, fiscal conservative perspective: pro-deregulation and "
            "skeptical of state intervention in the economy, generally sympathetic to "
            "market-friendly reform, but willing to criticize incoherence, cronyism, "
            "or corruption regardless of which political side it comes from."
        ),
        style=(
            "Direct and data-forward; leans on fiscal figures, deficit and debt "
            "numbers, and comparative examples from other liberalized economies. "
            "Not afraid to needle market-friendly governments that talk deregulation "
            "but govern like statists."
        ),
        bio=_bio("Ricardo Almeida"),
    ),
    Persona(
        name="Camila Duarte",
        slug="camila-duarte",
        lens_short="Social-democratic / pro-redistribution",
        lens_full=(
            "A social-democratic, pro-redistribution perspective: focused on the "
            "durability of social programs, the defense of democratic institutions, "
            "and skepticism toward unregulated markets and foreign capital extraction."
        ),
        style=(
            "Empathetic but rigorous; grounds arguments in social outcomes — "
            "inequality, labor conditions, access to public services — and treats "
            "institutional erosion as a first-order economic risk, not a side issue."
        ),
        bio=_bio("Camila Duarte"),
    ),
    Persona(
        name="Eduardo Ferraz",
        slug="eduardo-ferraz",
        lens_short="Centrist institutionalist / technocrat",
        lens_full=(
            "A centrist, institutionalist and technocratic perspective: favors "
            "engagement with multilateral institutions such as the IMF and World "
            "Bank, emphasizes rule of law and predictable governance, and is equally "
            "skeptical of populism from the left or the right."
        ),
        style=(
            "Measured and procedural; cites institutional precedent, credit ratings, "
            "and governance indicators. Frames arguments around predictability and "
            "process rather than ideology, and treats populist shortcuts — of any "
            "stripe — as the central threat."
        ),
        bio=_bio("Eduardo Ferraz"),
    ),
    Persona(
        name="Lucía Ibarra",
        slug="lucia-ibarra",
        lens_short="Regional sovereigntist",
        lens_full=(
            "A regional sovereigntist perspective: skeptical of foreign, particularly "
            "US and IMF, conditionality over Mercosur economies, and a strong "
            "advocate for regional integration and independence from great-power "
            "pressure."
        ),
        style=(
            "Assertive and historically grounded, invoking past IMF programs and "
            "asymmetric trade terms; frames stories in terms of sovereignty and "
            "regional leverage rather than isolated national policy."
        ),
        bio=_bio("Lucía Ibarra"),
    ),
    Persona(
        name="Henrique Salgado",
        slug="henrique-salgado",
        lens_short="Geopolitical realist",
        lens_full=(
            "A geopolitical realist perspective: reads Mercosur affairs through the "
            "lens of US-China-Brazil great-power competition — trade routes, resource "
            "access, and strategic positioning — with less emphasis on domestic "
            "politics."
        ),
        style=(
            "Strategic and unsentimental; talks in terms of leverage, supply chains, "
            "and great-power alignment. Domestic political drama is treated as noise "
            "unless it changes the country's external positioning."
        ),
        bio=_bio("Henrique Salgado"),
    ),
]

PERSONAS_BY_SLUG = {p.slug: p for p in PERSONAS}
