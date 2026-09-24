using Domain;

namespace BrewTrack.Tests;

public class L5BrewMathReservedTests
{
    [Fact]
    public void Plato_keeps_two_decimal_precision_for_light_wort()
    {
        Assert.Equal(10.48m, BrewMath.PlatoFromGravity(1.042m));
    }

    [Fact]
    public void Plato_keeps_two_decimal_precision_for_strong_wort()
    {
        Assert.Equal(20.01m, BrewMath.PlatoFromGravity(1.083m));
    }

    [Fact]
    public void Abv_keeps_two_decimal_precision_for_exact_quarter()
    {
        Assert.Equal(5.25m, BrewMath.AbvFromGravities(1.050m, 1.010m));
    }

    [Fact]
    public void Abv_keeps_two_decimal_precision_for_nontrivial_difference()
    {
        Assert.Equal(6.96m, BrewMath.AbvFromGravities(1.065m, 1.012m));
    }
}
