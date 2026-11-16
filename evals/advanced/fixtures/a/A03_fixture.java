import java.util.*;

class A03_fixture {
    public static void main(String[] args) {
        var base = new ArrayList<StringBuilder>();
        for (String s : List.of("A", "B", "C", "D"))
            base.add(new StringBuilder(s));
        var window = base.subList(1, 3);
        var copied = List.copyOf(window);
        var wrapped = Collections.unmodifiableList(window);
        window.set(0, new StringBuilder("B2"));
        base.get(2).append("!");
        System.out.println("base=" + base);
        System.out.println("copied=" + copied);
        System.out.println("wrapped=" + wrapped);
        try { copied.add(new StringBuilder("X")); }
        catch (UnsupportedOperationException e) {
            System.out.println("copied-add=blocked");
        }
        base.add(new StringBuilder("E"));
        try { System.out.println("window-size=" + window.size()); }
        catch (ConcurrentModificationException e) {
            System.out.println("window-size=invalidated");
        }
        System.out.println("copied-after=" + copied);
    }
}
