export const card_constants = JSON.parse(document.getElementById("card_constants").textContent);
export const userColors = [
	'#006BA4',
	'#FF800E',
	'#ABABAB',
	'#595959',
	'#5F9ED1',
	'#C85200',
];
export function toBase14(n) {
  return n.toString(14).toUpperCase();
}
