from partnersignal.seed import OPPORTUNITIES, SIGNALS


def test_every_opportunity_points_at_a_signal_for_the_same_partner_and_service():
    for row in OPPORTUNITIES:
        if row[1] is not None:
            signal = SIGNALS[row[1]]
            assert (signal[0], signal[4]) == (row[0], row[6]), row[2]


def test_seed_is_repeatable(session):
    from partnersignal.models import Activity, Opportunity, Signal

    counts = (session.query(Opportunity).count(), session.query(Signal).count(), session.query(Activity).count())
    from partnersignal.seed import seed

    seed(session)
    assert counts == (
        session.query(Opportunity).count(),
        session.query(Signal).count(),
        session.query(Activity).count(),
    )
