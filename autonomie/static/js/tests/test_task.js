/*
 * File Name : test_task.js
 *
 * Copyright (C) 2012 Gaston TJEBBES g.t@majerti.fr
 * Company : Majerti ( http://www.majerti.fr )
 *
 * This software is distributed under GPLV3
 * License: http://www.gnu.org/licenses/gpl-3.0.txt
 *
 */

function initTest(){
  var taskline1 = "<span id='test1' class='taskline'>" +
                "<input name='cost' value='100.25' />" +
                "<input name='quantity' value='1.25' />" +
                "<select name='tva'>" +
                "<option selected='selected' value='1960'>19.6%</option>" +
                "</select>" +
                "<div class='linetotal'><div class='input'></div></div></span>";
  var taskline2 = "<span id='test2' class='taskline'>" +
                "<input name='cost' value='100' />" +
                "<input name='quantity' value='1' />" +
                "<select name='tva'>" +
                "<option selected='selected' value='500'>5%</option>" +
                "</select>" +
                "<div class='linetotal'><div class='input'></div></div></span>";
  var line_total = "<div id='tasklines_ht'><div class='input'></div></div>";
  var discountline = "<span id='test-discount' class='discountline'>" +
                "<input name='amount' value='100' />" +
                "<select name='tva'>" +
                "<option selected='selected' value='1960'>19.6%</option>" +
                "</select>" +
                "<div class='linetotal'><div class='input'></div></div></span>";
  var total_ht = "<div id='total_ht'><div class='input'></div></div>";
  var tvalist = "<div id='tvalist'></div>";
  var total_ttc = "<div id='total_ttc'><div class='input'></div></div>";
  var total = "<div id='total'><div class='input'></div></div>";
  $('#qunit-fixture').html($(taskline1));
  $('#qunit-fixture').append($(taskline2));
  $('#qunit-fixture').append($(line_total));
  $('#qunit-fixture').append($(discountline));
  $('#qunit-fixture').append($(total_ht));
  $('#qunit-fixture').append($(tvalist));
  $('#qunit-fixture').append($(total_ttc));
  $('#qunit-fixture').append($(total));
}

var insecable = '\u00a0';
module("Fonctions générales");
test("Transformations des strings en centimes", function(){
  equal(transformToCents(), 0.0);
  equal(transformToCents("15,25"), 15.25);
  equal(transformToCents("15,25658"), 15.25658);
  equal(formatPrice(1), "1,00");
  equal(formatPrice(1.256, true), "1,25");
  equal(formatPrice(1.255555, false), "1,2555...");
  equal(formatPrice(1.2555, false), "1,2555");
  equal(isNotFormattable("150 €"), true);
  equal(isNotFormattable("150 "), false);
  equal(formatAmount(125), "125,00&nbsp;&euro;");
  equal(trailingZeros("1", false), "10");
  equal(trailingZeros("15", false), "15");
  equal(trailingZeros("1500", false), "15");
  equal(trailingZeros("1550", false), "155");
  equal(getIdFromTagId("abcdefgh_", "abcdefgh_2"), 2);
  // L'objet Date prend les mois en partant de janvier->0
  pdate = parseDate("2012-12-25");
  edate = new Date(2012, 11, 25);
  equal(pdate.year, edate.year);
  equal(pdate.month, edate.month);
  equal(pdate.day, edate.day);
});

test("Manipulation du DOM", function(){
  var line = "<div id='test'>Test</div>";
  $('#qunit-fixture').html($(line));
  delRow('test');
  var test = $('#test');
  equal($('#test').length, 0);
});
module("Objet ligne");
test("Ligne de prestation", function(){
  initTest();
  var row = new TaskRow('#test1');
  equal(row.tva, 1960);
  equal(row.ht, 125.3125);
  equal(row.tva_amount, 24.56125);
  equal(row.ttc, 149.87375);
  row.update();
  equal("125,3125" + insecable + "€", $('#test1 .linetotal .input').text());
});
test("Ligne de remise", function(){
  initTest();
  var row = new DiscountRow('#test-discount');
  equal(row.ht, -100);
  equal(row.tva, 1960);
  equal(row.tva_amount, -19.6);
  row.update();
  equal("-100,00" + insecable + "€", $('#test-discount .linetotal .input').text());
});
test("Groupe de ligne", function(){
  initTest();
  var collection = new RowCollection();
  collection.load('.taskline', TaskRow);
  equal(collection.models.length, 2);
  equal(collection.HT(), 225.3125);
  equal(collection.TTC(), 254.87375);
  var tvas = collection.Tvas();
  var expected = {1960:24.56125, 500:5};
  var index = 0;
  for (var key in tvas){
    equal(tvas[key], expected[key]);
  }
});
module("Lignes de paiement");
test("Contrôle sur le solde", function(){
  initTest();
  computeTotal();
  equal($('#tasklines_ht .input').text(), "225,3125" + insecable + '€');
  equal($('#total_ht .input').text(), '125,31' + insecable + '€');
  equal($('#total .input').text(), '135,27' + insecable + '€');
  equal(getTotal(), 135.27);
});